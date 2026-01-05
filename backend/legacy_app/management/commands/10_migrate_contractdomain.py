import os
from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import DGharar as LegacyDGharar
from contracts.models.models import ContractDomin

class Command(BaseCommand):
    help = 'Migrate DGharar to ContractDomin'

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
        
        # Get all legacy DGharar records
        legacy_records = LegacyDGharar.objects.using('legacy').all()
        total_count = legacy_records.count()
        
        self.stdout.write(f'Found {total_count} DGharar records in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for legacy_record in legacy_records:
            try:
                # Check if ContractDomin already exists with same code
                existing = ContractDomin.objects.filter(code=legacy_record.codetype).first()
                
                if existing:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping: ContractDomin with code {legacy_record.codetype} already exists '
                            f'(title: "{existing.title}")'
                        )
                    )
                    skipped_count += 1
                    continue
                
                if not dry_run:
                    with transaction.atomic():
                        # Create new ContractDomin record
                        new_contract_domin = ContractDomin.objects.create(
                            pk=legacy_record.pk,
                            title=legacy_record.gharartype,
                            code=legacy_record.codetype,
                        )
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created: ContractDomin "{new_contract_domin.title}" (code: {new_contract_domin.code})'
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Would create: ContractDomin "{legacy_record.gharartype}" (code: {legacy_record.codetype})'
                        )
                    )
                
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error migrating DGharar {legacy_record.pk} '
                        f'("{legacy_record.gharartype}"): {str(e)}'
                    )
                )
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total DGharar in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))