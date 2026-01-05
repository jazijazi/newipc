import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction, connections
from django.core.files import File
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from legacy_app.models import FeatureAttachment as LegacyFeatureAttachment
from accounts.models import User as NewUser
from layers.models.models import FeatureAttachment as NewFeatureAttachment
from contracts.models.SharhKhadamats import ShrhLayer as NewShrhLayer


class Command(BaseCommand):
    help = 'Migrate FeatureAttachment from old database to new with files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration without committing changes',
        )
        parser.add_argument(
            '--skip-files',
            action='store_true',
            help='Skip file copying (only migrate database records)',
        )
        parser.add_argument(
            '--legacy-media-root',
            type=str,
            default='/var/mediabck/',
            help='Path to legacy media root directory',
        )

    def get_new_content_type(self, old_content_type):
        """
        Map old content type to new content type.
        Replace 'prjapi_' with 'layers_' in the model name.
        """
        old_model_name = old_content_type.model
        
        # Replace prjapi_ with layers_
        if old_model_name.startswith('prjapi_'):
            new_model_name = old_model_name.replace('prjapi_', 'layers_', 1)
        else:
            new_model_name = old_model_name
        
        try:
            # Get the new content type
            new_content_type = ContentType.objects.get(model=new_model_name)
            return new_content_type
        except ContentType.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    f'Content type not found: {new_model_name} (from {old_model_name})'
                )
            )
            return None


    def get_new_object_id(self, old_content_type, old_object_id):
        """
        Get new object ID by:
        1. Query old layer table to get rprjgharar_id
        2. Find ShrhLayer with oldid = rprjgharar_id
        3. Query new layer table to get first record with shr_layer_id = ShrhLayer.id
        4. Return that record's id
        """

        old_table_name = old_content_type.model  # This is already the table name
        old_table_name = f'prjapi_{old_table_name}'

        try:
            # Get legacy database cursor
            legacy_cursor = connections['legacy'].cursor()
            
            # Query the old layer table to get rprjgharar_id
            legacy_cursor.execute(f"""
                SELECT "rprjgharar_id"
                FROM {old_table_name}
                WHERE id = %s
            """, [old_object_id])
            
            result = legacy_cursor.fetchone()
            legacy_cursor.close()
            
            if not result:
                self.stdout.write(
                    self.style.WARNING(
                        f'Record not found in {old_table_name} with id={old_object_id}'
                    )
                )
                return None
            
            rprjgharar_id = result[0]
            
            if not rprjgharar_id:
                self.stdout.write(
                    self.style.WARNING(
                        f'rprjgharar_id is NULL in {old_table_name} for id={old_object_id}'
                    )
                )
                return None
            
            # Find ShrhLayer with oldid = rprjgharar_id
            shrh_layer = NewShrhLayer.objects.filter(
                oldid=rprjgharar_id ,
                is_uploaded = True,
                layer_name__layername_en__iexact=old_content_type.model
            ).first()
            
            if not shrh_layer:
                self.stdout.write(
                    self.style.WARNING(
                        f'ShrhLayer not found with oldid={rprjgharar_id} '
                        f'(from {old_table_name}.id={old_object_id})'
                    )
                )
                return None
            
            # Now query the new layer table to get first record with shr_layer_id = shrh_layer.id
            new_table_name = old_table_name.replace('prjapi_', 'layers_', 1)
            print("old_table_name >>>>" , old_table_name)
            print("new_table_name >>>>" , new_table_name)
            
            default_cursor = connections['default'].cursor()
            
            default_cursor.execute(f"""
                SELECT id
                FROM {new_table_name}
                WHERE "shr_layer_id" = %s
                LIMIT 1
            """, [shrh_layer.id])
            
            new_result = default_cursor.fetchone()
            default_cursor.close()
            
            if not new_result:
                self.stdout.write(
                    self.style.WARNING(
                        f'Record not found in {new_table_name} with shr_layer_id={shrh_layer.id}'
                    )
                )
                return None
            
            return new_result[0]
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Error getting new object ID for {old_table_name}.id={old_object_id}: {str(e)}'
                )
            )
            return None


    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_files = options['skip_files']
        legacy_media_root = options['legacy_media_root']
        
        # Ensure legacy media root ends with /
        if not legacy_media_root.endswith('/'):
            legacy_media_root += '/'
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode - no changes will be saved'))
        
        if skip_files:
            self.stdout.write(self.style.WARNING('SKIPPING file copying - only migrating database records'))
        else:
            self.stdout.write(f'Legacy media root: {legacy_media_root}')
            self.stdout.write(f'New media root: {settings.MEDIA_ROOT}')
        
        # Get all legacy feature attachments
        legacy_attachments = LegacyFeatureAttachment.objects.using('legacy').select_related(
            'content_type', 'writer'
        ).all()
        total_count = legacy_attachments.count()
        
        self.stdout.write(f'Found {total_count} FeatureAttachment records in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        file_error_count = 0
        
        for legacy_attach in legacy_attachments:
            try:
                # Get new content type (prjapi_xxx -> layers_xxx)
                new_content_type = self.get_new_content_type(legacy_attach.content_type)
                
                if not new_content_type:
                    skipped_count += 1
                    continue
                
                # Get new object ID (query old layer table -> get rprjgharar_id -> find ShrhLayer)
                new_object_id = self.get_new_object_id(legacy_attach.content_type, legacy_attach.object_id)
                
                if not new_object_id:
                    skipped_count += 1
                    continue
                
                # Find corresponding user
                new_user = None
                if legacy_attach.writer:
                    new_user = NewUser.objects.filter(
                        username=legacy_attach.writer.username
                    ).first()
                
                # Check if attachment already exists
                file_name = os.path.basename(legacy_attach.file.name) if legacy_attach.file else ''
                existing = NewFeatureAttachment.objects.filter(
                    content_type=new_content_type,
                    object_id=new_object_id,
                    file__endswith=file_name
                ).exists()
                
                if existing:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping: Attachment "{file_name}" already exists for '
                            f'{new_content_type.model} (ShrhLayer id: {new_object_id})'
                        )
                    )
                    skipped_count += 1
                    continue
                
                if not dry_run:
                    with transaction.atomic():
                        # Create new attachment record
                        new_attachment = NewFeatureAttachment(
                            upload_date=legacy_attach.upload_date,
                            writer=new_user,
                            content_type=new_content_type,
                            object_id=new_object_id,
                            description=''
                        )
                        
                        # Handle file copying
                        if legacy_attach.file and not skip_files:
                            # Construct old file path
                            old_file_path = os.path.join(legacy_media_root, legacy_attach.file.name)
                            
                            self.stdout.write(
                                self.style.WARNING(f'OLD FILE PATH: {old_file_path}')
                            )
                            
                            if os.path.exists(old_file_path):
                                try:
                                    # Open and copy the file
                                    with open(old_file_path, 'rb') as f:
                                        file_name = os.path.basename(old_file_path)
                                        # Django will use the new upload_to path automatically
                                        new_attachment.file.save(file_name, File(f), save=False)
                                    
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f'Copied file: {old_file_path} -> '
                                            f'{new_content_type.model}/{new_object_id}/{file_name}'
                                        )
                                    )
                                except Exception as file_error:
                                    self.stdout.write(
                                        self.style.ERROR(f'Error copying file {old_file_path}: {str(file_error)}')
                                    )
                                    file_error_count += 1
                                    continue
                            else:
                                self.stdout.write(
                                    self.style.ERROR(f'File not found: {old_file_path}')
                                )
                                file_error_count += 1
                                continue
                        
                        new_attachment.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Migrated: FeatureAttachment for {new_content_type.model} '
                        f'(old: {legacy_attach.content_type.model}:{legacy_attach.object_id} -> '
                        f'new: {new_content_type.model}:ShrhLayer:{new_object_id})'
                    )
                )
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error migrating FeatureAttachment {legacy_attach.id}: {str(e)}'
                    )
                )
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total FeatureAttachment in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        self.stdout.write(self.style.ERROR(f'File errors: {file_error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))