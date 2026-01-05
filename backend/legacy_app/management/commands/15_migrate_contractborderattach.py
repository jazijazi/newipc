import os
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files import File
from django.conf import settings
from legacy_app.models import ProjectAttachment as LegacyProjectAttachment
from accounts.models import User as NewUser
from contracts.models.attachment import (
    ContractBorderAttachment as NewContractBorderAttachment,
    ContractBorderAttachmentDomain as NewContractBorderAttachmentDomain,
)
from contracts.models.models import (
    ContractBorder as NewContractBorder
)


class Command(BaseCommand):
    help = 'Migrate ProjectAttachment to ContractBorderAttachment with files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration without committing changes',
        )
        parser.add_argument(
            '--skip-files',
            action='store_true',
            help='Skip file copying (only migrate database records)',
        )
        parser.add_argument(
            '--legacy-media-root',
            type=str,
            default='/var/mediabck/',
            help='Path to legacy media root directory',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_files = options['skip_files']
        legacy_media_root = options['legacy_media_root']
        
        # Ensure legacy media root ends with /
        if not legacy_media_root.endswith('/'):
            legacy_media_root += '/'
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode - no changes will be saved'))
        
        if skip_files:
            self.stdout.write(self.style.WARNING('SKIPPING file copying - only migrating database records'))
        else:
            self.stdout.write(f'Legacy media root: {legacy_media_root}')
            self.stdout.write(f'New media root: {settings.MEDIA_ROOT}')
        
        # Get all legacy attachments
        legacy_attachments = LegacyProjectAttachment.objects.using('legacy').select_related(
            'rprjgharar', 'rprjgharar__project', 'rprjgharar__gharardad', 'dtyp', 'writer'
        ).all()
        total_count = legacy_attachments.count()
        
        self.stdout.write(f'Found {total_count} ProjectAttachment records in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        file_error_count = 0
        
        for legacy_attach in legacy_attachments:
            try:
                # Get the legacy project and gharardad
                if not legacy_attach.rprjgharar:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: Attachment {legacy_attach.id} has no rprjgharar')
                    )
                    skipped_count += 1
                    continue
                
                legacy_project = legacy_attach.rprjgharar.project
                legacy_gharardad = legacy_attach.rprjgharar.gharardad
                
                if not legacy_project or not legacy_gharardad:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: Attachment {legacy_attach.id} has no project or gharardad')
                    )
                    skipped_count += 1
                    continue
                
                # Find corresponding ContractBorder by oldid (project pk) and contract oldid (gharardad pk)
                new_contract_border = NewContractBorder.objects.filter(
                    oldid=legacy_project.pk,
                    contract__oldid=legacy_gharardad.pk
                ).first()
                
                if not new_contract_border:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping: ContractBorder not found for project {legacy_project.pk} '
                            f'and gharardad {legacy_gharardad.pk}'
                        )
                    )
                    skipped_count += 1
                    continue
                
                # Find corresponding attachment domain
                new_attach_domain = None
                if legacy_attach.dtyp:
                    new_attach_domain = NewContractBorderAttachmentDomain.objects.filter(
                        code=legacy_attach.dtyp.code
                    ).first()
                
                # Find corresponding user
                new_user = None
                if legacy_attach.writer:
                    new_user = NewUser.objects.filter(
                        username=legacy_attach.writer.username
                    ).first()
                
                # Check if attachment already exists (check by filename to avoid duplicates)
                file_name = os.path.basename(legacy_attach.file.name) if legacy_attach.file else ''
                existing = NewContractBorderAttachment.objects.filter(
                    contractborder=new_contract_border,
                    file__endswith=file_name
                ).exists()
                
                if existing:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping: Attachment "{file_name}" already exists for ContractBorder {new_contract_border.id}'
                        )
                    )
                    skipped_count += 1
                    continue
                
                if not dry_run:
                    with transaction.atomic():
                        # Create new attachment record
                        new_attachment = NewContractBorderAttachment(
                            upload_date=legacy_attach.upload_date,
                            writer=new_user,
                            contractborder=new_contract_border,
                            dtyp=new_attach_domain,
                        )
                        
                        # Handle file copying
                        if legacy_attach.file and not skip_files:
                            # Construct the old file path
                            old_file_path = os.path.join(legacy_media_root, legacy_attach.file.name)
                            
                            self.stdout.write(
                                self.style.WARNING(f'OLD FILE PATH: {old_file_path}')
                            )
                            
                            if os.path.exists(old_file_path):
                                # Open and copy the file
                                with open(old_file_path, 'rb') as f:
                                    file_name = os.path.basename(old_file_path)
                                    # This will save to: contracts/achments/contract_{contract_id}/contractborder_{contractborder_id}/{filename}
                                    new_attachment.file.save(file_name, File(f), save=False)
                                
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'Copied file: {old_file_path} -> '
                                        f'contract_{new_contract_border.contract.pk}/contractborder_{new_contract_border.id}/{file_name}'
                                    )
                                )
                            else:
                                self.stdout.write(
                                    self.style.ERROR(f'File not found: {old_file_path}')
                                )
                                file_error_count += 1
                                # Continue without file or skip this record
                                continue
                        
                        new_attachment.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Migrated: Attachment for ContractBorder {new_contract_border.id} '
                        f'(project: {legacy_project.pk}, gharardad: {legacy_gharardad.pk})'
                    )
                )
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error migrating attachment {legacy_attach.id}: {str(e)}'
                    )
                )
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total ProjectAttachment in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        self.stdout.write(self.style.ERROR(f'File errors: {file_error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))