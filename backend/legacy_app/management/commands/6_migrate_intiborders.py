from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import Tarh as LegacyTarh
from initialborders.models.models import InitialBorder as NewInitialBorder, InitialBorderDomin


class Command(BaseCommand):
    help = 'Migrate Tarh data from legacy database to new InitialBorder'

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
        
        # Get all Tarh records from legacy database
        legacy_tarhs = list(LegacyTarh.objects.using('legacy').all())
        total_count = len(legacy_tarhs)
        
        self.stdout.write(f'Found {total_count} Tarh records in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        # Dictionary to map old pk to new pk
        pk_mapping = {}
        
        # Keep track of records to process
        remaining_records = legacy_tarhs.copy()
        pass_number = 1
        max_passes = 10  # Prevent infinite loop
        
        while remaining_records and pass_number <= max_passes:
            self.stdout.write(self.style.WARNING(f'\n--- Pass {pass_number}: {len(remaining_records)} records remaining ---'))
            
            records_migrated_this_pass = 0
            still_remaining = []
            
            for legacy_tarh in remaining_records:
                try:
                    # Find matching InitialBorderDomin
                    new_domain = None
                    if legacy_tarh.dtarh:
                        new_domain = InitialBorderDomin.objects.filter(
                            title=legacy_tarh.dtarh.tarhtype,
                            code=legacy_tarh.dtarh.codetarh
                        ).first()
                        
                        if not new_domain:
                            self.stdout.write(
                                self.style.WARNING(f'Domain not found for {legacy_tarh.titletarh}')
                            )
                    
                    # Find new parent if exists
                    new_parent = None
                    if legacy_tarh.parentid:
                        old_parent_pk = legacy_tarh.parentid.pk
                        new_parent_pk = pk_mapping.get(old_parent_pk)
                        
                        if new_parent_pk:
                            new_parent = NewInitialBorder.objects.get(pk=new_parent_pk)
                        else:
                            # Parent not migrated yet, skip for now
                            still_remaining.append(legacy_tarh)
                            continue
                    
                    if not dry_run:
                        with transaction.atomic():
                            new_record = NewInitialBorder.objects.create(
                                title=legacy_tarh.titletarh or '',
                                dtyp=new_domain,
                                parentid=new_parent,
                                border=legacy_tarh.border
                            )
                            # Store the mapping
                            pk_mapping[legacy_tarh.pk] = new_record.pk
                    else:
                        # In dry run, simulate the mapping
                        pk_mapping[legacy_tarh.pk] = legacy_tarh.pk
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Migrated: {legacy_tarh.titletarh} (old pk: {legacy_tarh.pk})')
                    )
                    migrated_count += 1
                    records_migrated_this_pass += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error migrating {legacy_tarh.titletarh}: {str(e)}')
                    )
                    error_count += 1
            
            self.stdout.write(f'Pass {pass_number}: Migrated {records_migrated_this_pass} records')
            
            # If no records were migrated this pass, we have orphaned records
            if records_migrated_this_pass == 0 and still_remaining:
                self.stdout.write(self.style.ERROR(f'\nFound {len(still_remaining)} orphaned records (parent does not exist in legacy DB):'))
                for orphan in still_remaining:
                    self.stdout.write(self.style.ERROR(f'  - {orphan.titletarh} (pk: {orphan.pk}, parent_pk: {orphan.parentid.pk if orphan.parentid else None})'))
                skipped_count = len(still_remaining)
                break
            
            remaining_records = still_remaining
            pass_number += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total Tarh records in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped (orphaned/parent missing): {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        self.stdout.write(f'Total passes required: {pass_number - 1}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))
        else:
            self.stdout.write(self.style.SUCCESS('\nProvince relationships will be auto-calculated on save by the model'))