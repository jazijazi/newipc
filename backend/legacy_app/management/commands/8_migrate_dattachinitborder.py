from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import DTarhAttachment as LegacyDTarhAttachment
from initialborders.models.attachment import InitialBorderAttachmentDomain
from initialborders.models.models import InitialBorderDomin

class Command(BaseCommand):
    help = 'Migrate DTarhAttachment to InitialBorderAttachmentDomain'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration without committing changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode - no changes will be saved'))
        
        # Get all legacy attachment domain records
        legacy_attachments = LegacyDTarhAttachment.objects.using('legacy').all()
        total_count = legacy_attachments.count()
        
        self.stdout.write(f'Found {total_count} DTarhAttachment records in legacy database')
        
        migrated_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for legacy_attachment in legacy_attachments:
            try:
                # Find matching InitialBorderDomin
                new_initial_border_domain = None
                if legacy_attachment.dtarh:
                    new_initial_border_domain = InitialBorderDomin.objects.filter(
                        title=legacy_attachment.dtarh.tarhtype,
                        code=legacy_attachment.dtarh.codetarh
                    ).first()
                    
                    if not new_initial_border_domain:
                        self.stdout.write(
                            self.style.WARNING(f'InitialBorderDomin not found for {legacy_attachment.name} - creating without domain reference')
                        )
                
                if not dry_run:
                    with transaction.atomic():
                        # Prepare data
                        attachment_data = {
                            'name': legacy_attachment.name,
                            'category': legacy_attachment.category,
                            'dinitialborder': new_initial_border_domain,
                        }
                        
                        # Get or create by code
                        attachment_obj, created = InitialBorderAttachmentDomain.objects.get_or_create(
                            code=legacy_attachment.code,
                            defaults=attachment_data
                        )
                        
                        if not created:
                            # Update existing record
                            attachment_obj.name = legacy_attachment.name
                            attachment_obj.category = legacy_attachment.category
                            attachment_obj.dinitialborder = new_initial_border_domain
                            attachment_obj.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'Updated: {legacy_attachment.name} (code: {legacy_attachment.code})')
                            )
                        else:
                            migrated_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'Created: {legacy_attachment.name} (code: {legacy_attachment.code})')
                            )
                else:
                    # Dry run - check if exists
                    exists = InitialBorderAttachmentDomain.objects.filter(code=legacy_attachment.code).exists()
                    if exists:
                        self.stdout.write(
                            self.style.SUCCESS(f'Would update: {legacy_attachment.name} (code: {legacy_attachment.code})')
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f'Would create: {legacy_attachment.name} (code: {legacy_attachment.code})')
                        )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating {legacy_attachment.name}: {str(e)}')
                )
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total DTarhAttachment in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Created: {migrated_count}'))
        self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))