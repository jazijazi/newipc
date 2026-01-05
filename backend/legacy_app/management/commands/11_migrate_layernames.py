import os
from django.core.management.base import BaseCommand
from django.db import transaction

from legacy_app.models import Layers as LegacyLayers, DGharar as LegacyDGharar
from contracts.models.models import ContractDomin
from layers.models.models import LayersNames

class Command(BaseCommand):
    help = 'Migrate Layers to LayersNames'

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
        
        # Get all legacy layers
        legacy_layers = LegacyLayers.objects.using('legacy').select_related('dtyp_id').all()
        total_count = legacy_layers.count()
        
        self.stdout.write(f'Found {total_count} Layers records in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for legacy_layer in legacy_layers:
            try:
                # Find corresponding ContractDomin based on DGharar
                new_contract_domin = None
                if legacy_layer.dtyp_id:
                    legacy_dgharar = legacy_layer.dtyp_id
                    
                    # Match ContractDomin by gharartype and codetype
                    new_contract_domin = ContractDomin.objects.filter(
                        title=legacy_dgharar.gharartype,
                        code=legacy_dgharar.codetype
                    ).first()
                    
                    if not new_contract_domin:
                        self.stdout.write(
                            self.style.WARNING(
                                f'ContractDomin not found for DGharar: '
                                f'gharartype={legacy_dgharar.gharartype}, codetype={legacy_dgharar.codetype}'
                            )
                        )
                
                # Check if layer already exists to avoid duplicates
                existing = LayersNames.objects.filter(
                    dtyp = new_contract_domin,
                    lyrgroup_en=legacy_layer.lyrgroup_en,
                    lyrgroup_fa=legacy_layer.lyrgroup_fa,
                    layername_en=legacy_layer.layername_en,
                    layername_fa=legacy_layer.layername_fa,
                    geometrytype=legacy_layer.geometrytype
                ).exists()
                
                if existing:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping: LayersNames already exists for '
                            f'"{legacy_layer.layername_fa or legacy_layer.layername_en}"'
                        )
                    )
                    skipped_count += 1
                    continue
                
                if not dry_run:
                    with transaction.atomic():
                        # Create new LayersNames record
                        new_layer = LayersNames.objects.create(
                            dtyp=new_contract_domin,
                            lyrgroup_en=legacy_layer.lyrgroup_en,
                            lyrgroup_fa=legacy_layer.lyrgroup_fa,
                            layername_en=legacy_layer.layername_en,
                            layername_fa=legacy_layer.layername_fa,
                            geometrytype=legacy_layer.geometrytype,
                        )
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created LayersNames: "{new_layer.layername_fa or new_layer.layername_en}" '
                                f'(ID: {new_layer.id})'
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Would create LayersNames: "{legacy_layer.layername_fa or legacy_layer.layername_en}"'
                        )
                    )
                
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error migrating layer {legacy_layer.id}: {str(e)}'
                    )
                )
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total Layers in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))