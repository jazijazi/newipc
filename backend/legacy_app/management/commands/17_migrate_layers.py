from django.core.management.base import BaseCommand
from django.db import transaction, connections
from legacy_app.models import (
    Sharhkadamat as LegacySharhkadamat,
)
from accounts.models import User as NewUser
from contracts.models.SharhKhadamats import (
    ShrhBase as NewShrhBase,
    ShrhLayer as NewShrhLayer,
)
from contracts.models.models import (
    ContractBorder as NewContractBorder,
)
from layers.models.models import (
    LayersNames as NewLayersNames,
)

class Command(BaseCommand):
    help = 'Migrate Layers from old database to new'


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
        
        all_sharhlayers = NewShrhLayer.objects.filter(
            is_uploaded = True
        )

        self.stdout.write(self.style.SUCCESS(f'found {all_sharhlayers.count()} sharlayer with is_uploaded true in new database'))
        
        migrated_base_count = 0
        migrated_layer_count = 0
        skipped_count = 0
        error_count = 0

        # Get database cursors
        legacy_cursor = connections['legacy'].cursor()
        default_cursor = connections['default'].cursor()

        for shrlyr in all_sharhlayers:
            try:
                sharlyer_layername = shrlyr.layer_name if shrlyr.layer_name else None
                if sharlyer_layername is None:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: sharhlayer {shrlyr.id} has no layername at all !')
                    )
                    skipped_count += 1
                    continue
                if shrlyr.oldid is None:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: sharhlayer {shrlyr.id} has no oldid(prjghararid) for migrate !')
                    )
                    skipped_count += 1
                    continue

                layer_name_en = shrlyr.layer_name.layername_en
                old_prjgharar = shrlyr.oldid

                # Construct table names
                old_table_name = f"prjapi_{layer_name_en}".lower()
                new_table_name = f"layers_{layer_name_en}".lower()

                self.stdout.write(
                    self.style.WARNING(f'Processing layer: {layer_name_en}, oldid: {old_prjgharar}')
                )

                # Check if old table exists
                legacy_cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, [old_table_name])
                
                old_table_exists = legacy_cursor.fetchone()[0]
                
                if not old_table_exists:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: Table {old_table_name} does not exist in legacy database')
                    )
                    skipped_count += 1
                    continue

                # Check if new table exists
                default_cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, [new_table_name])
                
                new_table_exists = default_cursor.fetchone()[0]
                
                if not new_table_exists:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: Table {new_table_name} does not exist in new database')
                    )
                    skipped_count += 1
                    continue

                # Get column names from old table (excluding rprjgharar_id)
                legacy_cursor.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    AND column_name != 'rprjgharar_id'
                    ORDER BY ordinal_position
                """, [old_table_name])
                
                columns = [row[0] for row in legacy_cursor.fetchall()]
                
                if not columns:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: No columns found in {old_table_name}')
                    )
                    skipped_count += 1
                    continue

                # Fetch records from old table
                columns_quoted = [f'"{col}"' for col in columns]
                columns_str = ', '.join(columns_quoted)
                legacy_cursor.execute(f"""
                    SELECT {columns_str}
                    FROM {old_table_name}
                    WHERE rprjgharar_id = %s
                """, [old_prjgharar])
                
                records = legacy_cursor.fetchall()
                
                if not records:
                    self.stdout.write(
                        self.style.WARNING(f'No records found in {old_table_name} for rprjgharar_id={old_prjgharar}')
                    )
                    skipped_count += 1
                    continue

                self.stdout.write(
                    self.style.SUCCESS(f'Found {len(records)} records in {old_table_name}')
                )

                # Insert records into new table
                if not dry_run:
                    # Add shr_layer_id to columns list
                    new_columns = columns + ['shr_layer_id']
                    new_columns_quoted = [f'"{col}"' for col in new_columns]
                    new_columns_str = ', '.join(new_columns_quoted)
                    
                    # Create placeholders for values
                    placeholders = ', '.join(['%s'] * len(new_columns))
                    
                    inserted_count = 0
                    for record in records:
                        # Add shr_layer_id value to the record
                        new_record = list(record) + [shrlyr.id]
                        
                        try:
                            default_cursor.execute(f"""
                                INSERT INTO {new_table_name} ({new_columns_str})
                                VALUES ({placeholders})
                            """, new_record)
                            inserted_count += 1
                        except Exception as insert_error:
                            self.stdout.write(
                                self.style.ERROR(f'Error inserting record into {new_table_name}: {str(insert_error)}')
                            )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Inserted {inserted_count} records into {new_table_name}')
                    )
                    migrated_layer_count += inserted_count
                else:
                    self.stdout.write(
                        self.style.WARNING(f'DRY RUN: Would insert {len(records)} records into {new_table_name}')
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating layer {shrlyr.id}: {str(e)}')
                )
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                error_count += 1
        
        # Close cursors
        legacy_cursor.close()
        default_cursor.close()
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total SharhLayer for Migrate: {all_sharhlayers.count()}')
        self.stdout.write(self.style.SUCCESS(f'Total records migrated: {migrated_layer_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped layers: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))