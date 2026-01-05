from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import Ostans as LegacyOstans
from common.models import Province


class Command(BaseCommand):
    help = 'Migrate province data from legacy database to new database'

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
        
        # Get all provinces from legacy database
        legacy_provinces = LegacyOstans.objects.using('legacy').all()
        total_count = legacy_provinces.count()
        
        self.stdout.write(f'Found {total_count} provinces in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0

        province_code = 100
        
        for legacy_province in legacy_provinces:
            try:
                # Check if province already exists in new database
                exists = Province.objects.filter(name_fa=legacy_province.name_fa).exists()
                
                if exists:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: {legacy_province.name_fa} - already exists')
                    )
                    skipped_count += 1
                    continue
                
                if not dry_run:
                    with transaction.atomic():
                        Province.objects.create(
                            name_fa=legacy_province.name_fa,
                            cnter_name_fa = legacy_province.name_fa,
                            code=province_code,
                            border=legacy_province.border
                        )
                        province_code += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f'Migrated: {legacy_province.name_fa} ({legacy_province.name_en})')
                )
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating {legacy_province.name_fa}: {str(e)}')
                )
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total provinces in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped (already exists): {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))