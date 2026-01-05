from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import (
    Tarh as LegacyTarh,
    TarhShnPahneh,
    TarhShnDarkhastekteshaf,
    TarhShnParvaneekteshaf,
    TarhShnGovahikashf,
    TarhShnParvanebahrebardai,
    TarhShnPotansielyabi
)

from initialborders.models.models import (
    InitialBorder as NewInitialBorder,
)

from initialborders.models.metadata import (
    InitialBorderMetadataPahneh,
    InitialBorderMetadataDarkhastekteshaf,
    InitialBorderMetadataParvaneekteshaf,
    InitialBorderMetadataGovahikashf,
    InitialBorderMetadataParvanebahrebardai,
    InitialBorderMetadataPotansielyabi
)

class Command(BaseCommand):
    help = 'Migrate InitialBorder metadata from legacy Tarh Shenasnameh'

    # Map legacy metadata classes to new metadata classes
    METADATA_MAPPING = {
        'TarhShnPahneh': (TarhShnPahneh, InitialBorderMetadataPahneh, []),
        'TarhShnDarkhastekteshaf': (TarhShnDarkhastekteshaf, InitialBorderMetadataDarkhastekteshaf, ['cadastre', 'noemademadani', 'organs']),
        'TarhShnParvaneekteshaf': (TarhShnParvaneekteshaf, InitialBorderMetadataParvaneekteshaf, ['cadastre', 'noemademadani', 'shomareparvaneh', 'tarikhparvane', 'tarikhetebar']),
        'TarhShnGovahikashf': (TarhShnGovahikashf, InitialBorderMetadataGovahikashf, ['cadastre', 'noemademadani', 'shomareparvaneh', 'tarikhparvane', 'tarietebargovahi', 'zakhireehtemali', 'zakhireghatei', 'ayarehad', 'ayaremeyangin', 'shomaregovahikashf', 'tarikhsodurgivahikashf']),
        'TarhShnParvanebahrebardai': (TarhShnParvanebahrebardai, InitialBorderMetadataParvanebahrebardai, ['cadastre', 'noemademadani', 'shomareparvaneh', 'tarikhparvane', 'tarietebarparvane', 'zakhireehtemali', 'zakhireghatei', 'ayarehad', 'ayaremeyangin', 'estekhrajsaleyane']),
        'TarhShnPotansielyabi': (TarhShnPotansielyabi, InitialBorderMetadataPotansielyabi, ['noemademadani']),
    }

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
        
        total_migrated = 0
        total_updated = 0
        total_skipped = 0
        total_errors = 0
        
        # Process each metadata type
        for class_name, (LegacyMetadataClass, NewMetadataClass, extra_fields) in self.METADATA_MAPPING.items():
            self.stdout.write(self.style.WARNING(f'\n--- Processing {class_name} ---'))
            
            # Get all legacy metadata records
            legacy_metadata_records = LegacyMetadataClass.objects.using('legacy').all()
            count = legacy_metadata_records.count()
            self.stdout.write(f'Found {count} {class_name} records in legacy database')
            
            migrated = 0
            updated = 0
            skipped = 0
            errors = 0
            
            for legacy_meta in legacy_metadata_records:
                try:
                    # Find the corresponding new InitialBorder by matching the old Tarh
                    legacy_tarh_id = legacy_meta.rtarh.pk
                    
                    # Try to find the new InitialBorder with the same title as the old Tarh
                    legacy_tarh_title = legacy_meta.rtarh.titletarh
                    new_initial_border = NewInitialBorder.objects.filter(title=legacy_tarh_title).first()
                    
                    if not new_initial_border:
                        self.stdout.write(
                            self.style.WARNING(f'Skipping: InitialBorder not found for Tarh "{legacy_tarh_title}" (pk: {legacy_tarh_id})')
                        )
                        skipped += 1
                        continue
                    
                    if not dry_run:
                        with transaction.atomic():
                            # Prepare common fields
                            metadata_data = {
                                'name': legacy_meta.name,
                                'masahat': legacy_meta.masahat,
                                'malekiyat': legacy_meta.malekiyat,
                                'ostan': legacy_meta.ostan,
                                'shahrestan': legacy_meta.shahrestan,
                            }
                            
                            # Add extra fields specific to this metadata type
                            for field in extra_fields:
                                if hasattr(legacy_meta, field):
                                    metadata_data[field] = getattr(legacy_meta, field)
                            
                            # Get or create metadata
                            metadata_obj, created = NewMetadataClass.objects.get_or_create(
                                rinitialborder=new_initial_border,
                                defaults=metadata_data
                            )
                            
                            if not created:
                                # Update existing metadata
                                for field, value in metadata_data.items():
                                    setattr(metadata_obj, field, value)
                                metadata_obj.save()
                                updated += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f'Updated: {class_name} for "{legacy_tarh_title}"')
                                )
                            else:
                                migrated += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f'Created: {class_name} for "{legacy_tarh_title}"')
                                )
                    else:
                        # In dry run, just report what would happen
                        existing = NewMetadataClass.objects.filter(rinitialborder=new_initial_border).exists()
                        if existing:
                            self.stdout.write(
                                self.style.SUCCESS(f'Would update: {class_name} for "{legacy_tarh_title}"')
                            )
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(f'Would create: {class_name} for "{legacy_tarh_title}"')
                            )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error migrating {class_name} for Tarh pk {legacy_meta.rtarh.pk}: {str(e)}')
                    )
                    errors += 1
            
            self.stdout.write(f'{class_name} - Created: {migrated}, Updated: {updated}, Skipped: {skipped}, Errors: {errors}')
            total_migrated += migrated
            total_updated += updated
            total_skipped += skipped
            total_errors += errors
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(self.style.SUCCESS(f'Total created: {total_migrated}'))
        self.stdout.write(self.style.SUCCESS(f'Total updated: {total_updated}'))
        self.stdout.write(self.style.WARNING(f'Total skipped: {total_skipped}'))
        self.stdout.write(self.style.ERROR(f'Total errors: {total_errors}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))