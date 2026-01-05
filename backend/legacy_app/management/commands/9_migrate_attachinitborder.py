import os
import shutil
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files import File
from django.conf import settings
from legacy_app.models import TarhAttachment as LegacyTarhAttachment

from accounts.models import User as NewUser

from initialborders.models.attachment import InitialBorderAttachment, InitialBorderAttachmentDomain
from initialborders.models.models import InitialBorder

class Command(BaseCommand):
    help = 'Migrate TarhAttachment to InitialBorderAttachment with files'

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
        legacy_attachments = LegacyTarhAttachment.objects.using('legacy').select_related(
            'rtarh', 'rtarh__dtarh', 'dtyp_attach'
        ).all()
        total_count = legacy_attachments.count()
        
        self.stdout.write(f'Found {total_count} TarhAttachment records in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        file_error_count = 0
        
        for legacy_attach in legacy_attachments:
            try:
                # Find corresponding InitialBorder based on title AND dtarh type
                legacy_tarh_title = legacy_attach.rtarh.titletarh
                legacy_dtarh_code = legacy_attach.rtarh.dtarh.codetarh if legacy_attach.rtarh.dtarh else None
                
                # Match by both title and domain code for better accuracy
                query = InitialBorder.objects.filter(title=legacy_tarh_title)
                if legacy_dtarh_code:
                    query = query.filter(dtyp__code=legacy_dtarh_code)
                
                new_initial_border = query.first()
                
                if not new_initial_border:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping: InitialBorder not found for "{legacy_tarh_title}" '
                            f'(dtarh code: {legacy_dtarh_code})'
                        )
                    )
                    skipped_count += 1
                    continue
                
                # Find corresponding attachment domain
                new_attach_domain = None
                if legacy_attach.dtyp_attach:
                    new_attach_domain = InitialBorderAttachmentDomain.objects.filter(
                        code=legacy_attach.dtyp_attach.code
                    ).first()

                new_attachment_writer = None
                if legacy_attach.writer:
                    new_attachment_writer = NewUser.objects.filter(
                        username=legacy_attach.writer.username
                    ).first()
                
                # Check if attachment already exists (check by filename to avoid duplicates)
                file_name = os.path.basename(legacy_attach.file.name) if legacy_attach.file else ''
                existing = InitialBorderAttachment.objects.filter(
                    rinitialborder=new_initial_border,
                    file__endswith=file_name
                ).exists()
                
                if existing:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping: Attachment "{file_name}" already exists for "{legacy_tarh_title}"'
                        )
                    )
                    skipped_count += 1
                    continue

                old_file_path = os.path.join(legacy_media_root, legacy_attach.file.name)

                self.stdout.write(
                    self.style.WARNING(
                        f'OLD FILE PATH {old_file_path}'
                    )
                )
                
                if not dry_run:
                    with transaction.atomic():
                        # Create new attachment record
                        new_attachment = InitialBorderAttachment(
                            upload_date=legacy_attach.upload_date,
                            writer=new_attachment_writer,
                            writed_date=legacy_attach.writed_date,
                            rinitialborder=new_initial_border,
                            dtyp_attach=new_attach_domain,
                        )
                        
                        # Handle file copying
                        if legacy_attach.file and not skip_files:
                            # Construct the old file path using legacy media root
                            # legacy_attach.file.name contains the relative path like:
                            # 'prjapi/tarhattachments/tarh_453/file.pdf'
                            old_file_path = os.path.join(legacy_media_root, legacy_attach.file.name)

                            if os.path.exists(old_file_path):
                                # Open and copy the file
                                # Django will automatically use the NEW ID in the upload path
                                with open(old_file_path, 'rb') as f:
                                    file_name = os.path.basename(old_file_path)
                                    # This will save to: initialborder/achments/initialborder_{NEW_ID}/{filename}
                                    new_attachment.file.save(file_name, File(f), save=False)
                                
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'Copied file: {old_file_path} -> '
                                        f'initialborder_{new_initial_border.id}/{file_name}'
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
                        f'Migrated: Attachment for "{legacy_tarh_title}" '
                        f'(old ID: {legacy_attach.rtarh.id} -> new ID: {new_initial_border.id})'
                    )
                )
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error migrating attachment {legacy_attach.id} '
                        f'for Tarh {legacy_attach.rtarh.pk}: {str(e)}'
                    )
                )
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total TarhAttachment in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        self.stdout.write(self.style.ERROR(f'File errors: {file_error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))