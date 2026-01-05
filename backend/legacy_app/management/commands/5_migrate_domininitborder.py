from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import DTarh
from initialborders.models.models import InitialBorderDomin


class Command(BaseCommand):
    help = 'Migrate DTarh data from legacy database to InitialBorderDomin in new database'

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
        
        # Get all records from legacy database
        legacy_records = DTarh.objects.using('legacy').all()
        total_count = legacy_records.count()
        
        self.stdout.write(f'Found {total_count} records in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for legacy_record in legacy_records:
            try:
                # Check if record already exists in new database
                exists = InitialBorderDomin.objects.filter(code=legacy_record.codetarh).exists()
                
                if exists:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: {legacy_record.tarhtype} (code: {legacy_record.codetarh}) - already exists')
                    )
                    skipped_count += 1
                    continue
                
                if not dry_run:
                    with transaction.atomic():
                        InitialBorderDomin.objects.create(
                            pk = legacy_record.pk,
                            title=legacy_record.tarhtype,
                            code=legacy_record.codetarh
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Migrated: {legacy_record.tarhtype} (code: {legacy_record.codetarh})')
                )
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating {legacy_record.tarhtype}: {str(e)}')
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