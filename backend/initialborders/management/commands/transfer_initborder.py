import json
import os
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry
from initialborders.models.models import InitialBorder, InitialBorderDomin

class Command(BaseCommand):
    help = 'Transfer old Tarh data to new InitialBorder model'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to the JSON file containing old Tarh data'
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        
        if not os.path.exists(json_file):
            self.stdout.write(self.style.ERROR(f'File not found: {json_file}'))
            return
        
        # Check file size
        file_size = os.path.getsize(json_file)
        if file_size == 0:
            self.stdout.write(self.style.ERROR(f'File is empty: {json_file}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'File size: {file_size} bytes'))
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    self.stdout.write(self.style.ERROR('File content is empty'))
                    return
                
                # Find the first '[' character to skip any preamble
                json_start = content.find('[')
                if json_start == -1:
                    self.stdout.write(self.style.ERROR('No JSON array found in file'))
                    return
                
                if json_start > 0:
                    self.stdout.write(self.style.WARNING(f'Skipping {json_start} characters of preamble'))
                    content = content[json_start:]
                
                data = json.loads(content)
                
        except UnicodeDecodeError:
            self.stdout.write(self.style.WARNING('UTF-8 failed, trying latin-1...'))
            with open(json_file, 'r', encoding='latin-1') as f:
                content = f.read()
                json_start = content.find('[')
                if json_start > 0:
                    content = content[json_start:]
                data = json.loads(content)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'JSON decode error: {str(e)}'))
            return
        
        if not isinstance(data, list):
            self.stdout.write(self.style.ERROR('JSON root must be a list'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(data)} records from {json_file}'))
        
        # Track statistics
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        # First pass: create all records without parent relationships
        pk_mapping = {}  # Map old PKs to new instances
        
        for item in data:
            try:
                fields = item['fields']
                old_pk = item['pk']
                
                # Get the related InitialBorderDomin if dtarh exists
                dtyp_instance = None
                if fields.get('dtarh'):
                    try:
                        # dtarh is FK, so it's the PK of DTarh, not the code
                        # We need to find InitialBorderDomin by its PK if you transferred manually
                        # Or find by code - need clarification on how you transferred
                        dtyp_instance = InitialBorderDomin.objects.get(pk=fields['dtarh'])
                    except InitialBorderDomin.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"InitialBorderDomin with pk {fields['dtarh']} not found")
                        )
                
                # Parse border geometry
                border_geom = None
                if fields.get('border'):
                    border_geom = GEOSGeometry(fields['border'])
                
                # Skip if no border (required field in new model)
                if not border_geom:
                    self.stdout.write(
                        self.style.WARNING(f"Skipping record {old_pk}: no border geometry")
                    )
                    skipped_count += 1
                    continue
                
                # Create new InitialBorder (without parent for now)
                new_instance = InitialBorder.objects.create(
                    title=fields.get('titletarh', ''),
                    border=border_geom,
                    dtyp=dtyp_instance,
                    parentid=None  # Will set in second pass
                )
                
                pk_mapping[old_pk] = new_instance
                created_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f"Created InitialBorder: {new_instance.title} (old pk: {old_pk})")
                )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"Error processing record {item.get('pk')}: {str(e)}")
                )
        
        # Second pass: set parent relationships
        self.stdout.write(self.style.SUCCESS('\nSetting parent relationships...'))
        
        for item in data:
            try:
                fields = item['fields']
                old_pk = item['pk']
                old_parent_id = fields.get('parentid')
                
                if old_pk in pk_mapping and old_parent_id:
                    if old_parent_id in pk_mapping:
                        new_instance = pk_mapping[old_pk]
                        new_instance.parentid = pk_mapping[old_parent_id]
                        new_instance.save()
                        self.stdout.write(
                            self.style.SUCCESS(f"Set parent for {new_instance.title}")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"Parent {old_parent_id} not found for record {old_pk}")
                        )
                        
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"Error setting parent for record {item.get('pk')}: {str(e)}")
                )
        
        # Print summary
        self.stdout.write(self.style.SUCCESS('\n=== Transfer Summary ==='))
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))