import os
import shutil
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from legacy_app.models import RasterData as LegacyRasterData
from contracts.models.SharhKhadamats import ShrhLayer as NewShrhLayer


class Command(BaseCommand):
    help = 'Migrate RasterData UUIDs to ShrhLayer raster_uuid field and copy raster files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration without committing changes',
        )
        parser.add_argument(
            '--old-raster-dir',
            type=str,
            default='/var/raster/',
            help='Path to old raster directory',
        )
        parser.add_argument(
            '--skip-files',
            action='store_true',
            help='Skip file copying (only migrate database records)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_files = options['skip_files']
        old_raster_dir = options['old_raster_dir']
        
        # Ensure old raster dir ends with /
        if not old_raster_dir.endswith('/'):
            old_raster_dir += '/'
        
        # Get new raster dir from settings
        new_raster_dir = getattr(settings, 'RASTER_ROOT', None)
        
        if not new_raster_dir:
            self.stdout.write(self.style.ERROR('RASTER_ROOT is not defined in settings'))
            return
        
        # Ensure new raster dir ends with /
        if not new_raster_dir.endswith('/'):
            new_raster_dir += '/'
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode - no changes will be saved'))
        
        if skip_files:
            self.stdout.write(self.style.WARNING('SKIPPING file copying - only migrating database records'))
        else:
            self.stdout.write(f'Old raster directory: {old_raster_dir}')
            self.stdout.write(f'New raster directory: {new_raster_dir}')
        
        # Get all RasterData records from legacy database
        raster_records = LegacyRasterData.objects.using('legacy').select_related('sharhkadamat').all()
        total_count = raster_records.count()
        
        self.stdout.write(f'Found {total_count} RasterData records in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        file_error_count = 0
        
        for raster in raster_records:
            try:
                # Find corresponding ShrhLayer by oldid (which is the old sharhkadamat pk)
                shrh_layer = NewShrhLayer.objects.filter(
                    oldid = raster.sharhkadamat.prjgharar.id,
                    layer_name__dtyp__code = raster.sharhkadamat.layer.dtyp_id.codetype,
                    layer_name__lyrgroup_en = raster.sharhkadamat.layer.lyrgroup_en ,
                    layer_name__lyrgroup_fa = raster.sharhkadamat.layer.lyrgroup_fa ,
                    layer_name__layername_en = raster.sharhkadamat.layer.layername_en ,
                    layer_name__layername_fa = raster.sharhkadamat.layer.layername_fa ,
                    layer_name__geometrytype = raster.sharhkadamat.layer.geometrytype ,
                ).first()
                
                if not shrh_layer:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping: ShrhLayer not found for sharhkadamat_id={raster.sharhkadamat.pk} '
                            f'(RasterData id: {raster.id})'
                        )
                    )
                    skipped_count += 1
                    continue
                
                # Check if raster_uuid is already set
                if shrh_layer.raster_uuid:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping: ShrhLayer {shrh_layer.id} already has raster_uuid: {shrh_layer.raster_uuid}'
                        )
                    )
                    skipped_count += 1
                    continue
                
                # Handle file copying
                file_copied = True
                if not skip_files:
                    # Construct old file path: /var/raster/{uuid}/output_cog.tif
                    old_file_path = os.path.join(old_raster_dir, raster.uuid, 'output_cog.tif')
                    
                    # Construct new file path: {RASTER_ROOT}/{uuid}/output_cog.tif
                    new_file_dir = os.path.join(new_raster_dir, raster.uuid)
                    new_file_path = os.path.join(new_file_dir, 'output_cog.tif')
                    
                    if os.path.exists(old_file_path):
                        if not dry_run:
                            try:
                                # Create directory if it doesn't exist
                                os.makedirs(new_file_dir, exist_ok=True)
                                
                                # Copy the file
                                shutil.copy2(old_file_path, new_file_path)
                                
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'Copied file: {old_file_path} -> {new_file_path}'
                                    )
                                )
                            except Exception as file_error:
                                self.stdout.write(
                                    self.style.ERROR(f'Error copying file {old_file_path}: {str(file_error)}')
                                )
                                file_error_count += 1
                                file_copied = False
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'DRY RUN: Would copy {old_file_path} -> {new_file_path}')
                            )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'File not found: {old_file_path}')
                        )
                        file_error_count += 1
                        file_copied = False
                
                # Update database only if file was copied successfully (or skipping files)
                if file_copied or skip_files:
                    if not dry_run:
                        with transaction.atomic():
                            shrh_layer.raster_uuid = raster.uuid
                            shrh_layer.save(update_fields=['raster_uuid'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Migrated: RasterData {raster.id} -> ShrhLayer {shrh_layer.id} (UUID: {raster.uuid})'
                        )
                    )
                    migrated_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping database update for ShrhLayer {shrh_layer.id} due to file copy failure'
                        )
                    )
                    skipped_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating RasterData {raster.id}: {str(e)}')
                )
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total RasterData records in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        self.stdout.write(self.style.ERROR(f'File errors: {file_error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))