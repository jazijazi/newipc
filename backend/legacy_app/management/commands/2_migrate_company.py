from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import SherkatEjraei
from common.models import Company


class Command(BaseCommand):
    help = 'Migrate company data from legacy database to new database'

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
        
        # Get all companies from legacy database
        legacy_companies = SherkatEjraei.objects.using('legacy').all()
        total_count = legacy_companies.count()
        
        self.stdout.write(f'Found {total_count} companies in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for legacy_company in legacy_companies:
            try:
                # Check if company already exists in new database (by name since it's unique now)
                exists = Company.objects.filter(name=legacy_company.name).exists()
                
                if exists:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: {legacy_company.name} - already exists')
                    )
                    skipped_count += 1
                    continue
                
                if not dry_run:
                    with transaction.atomic():
                        Company.objects.create(
                            pk=legacy_company.pk,
                            name=legacy_company.name,
                            code=legacy_company.code,
                            typ=legacy_company.typ,
                            service_typ=legacy_company.service_typ,
                            callnumber=legacy_company.callnumber,
                            address=legacy_company.address,
                            comment=legacy_company.comment
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Migrated: {legacy_company.name}')
                )
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating {legacy_company.name}: {str(e)}')
                )
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total companies in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped (already exists): {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))