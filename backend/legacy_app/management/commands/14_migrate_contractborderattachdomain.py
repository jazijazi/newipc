from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import DPrjAttach as LegacyDPrjAttach
from contracts.models.attachment import ContractBorderAttachmentDomain as NewContractBorderAttachmentDomain


class Command(BaseCommand):
    help = 'Migrate DPrjAttach to ContractBorderAttachmentDomain'

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
        
        legacy_domains = LegacyDPrjAttach.objects.using('legacy').all()
        total_count = legacy_domains.count()
        
        self.stdout.write(f'Found {total_count} ContractBorderAttachmentDomain records in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for legacy_domain in legacy_domains:
            try:
                # Check if already exists
                exists = NewContractBorderAttachmentDomain.objects.filter(
                    code=legacy_domain.code
                ).exists()
                
                if exists:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: {legacy_domain.name_fa} - already exists')
                    )
                    skipped_count += 1
                    continue
                
                if not dry_run:
                    with transaction.atomic():
                        NewContractBorderAttachmentDomain.objects.create(
                            pk= legacy_domain.pk,
                            code=legacy_domain.code,
                            name_en=legacy_domain.name_en,
                            name_fa=legacy_domain.name_fa,
                            typ=legacy_domain.typ
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Migrated: {legacy_domain.name_fa} ({legacy_domain.name_en})')
                )
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating {legacy_domain.name_fa}: {str(e)}')
                )
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total records in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped (already exists): {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))