import json
import os
from django.core.management.base import BaseCommand
from initialborders.models.models import InitialBorderAttachmentDomain, InitialBorderDomin


class Command(BaseCommand):
    help = 'Transfer old DTarhAttachment data to new InitialBorderAttachmentDomain model'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to the JSON file containing old DTarhAttachment data'
        )

    def load_json(self, file_path):
        """Load and parse JSON file, skipping any preamble"""
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            json_start = content.find('[')
            if json_start == -1:
                self.stdout.write(self.style.ERROR(f'No JSON array found in {file_path}'))
                return None
            
            if json_start > 0:
                self.stdout.write(self.style.WARNING(f'Skipping {json_start} characters of preamble'))
                content = content[json_start:]
            
            return json.loads(content)

    def handle(self, *args, **options):
        json_file = options['json_file']
        
        data = self.load_json(json_file)
        if not data:
            return
        
        file_size = os.path.getsize(json_file)
        self.stdout.write(self.style.SUCCESS(f'File size: {file_size} bytes'))
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(data)} records from {json_file}'))
        
        # Statistics
        created_count = 0
        error_count = 0
        
        for item in data:
            try:
                fields = item['fields']
                old_pk = item['pk']
                
                # Get InitialBorderDomin FK (was dtarh)
                dinitialborder_instance = None
                if fields.get('dtarh'):
                    try:
                        dinitialborder_instance = InitialBorderDomin.objects.get(pk=fields['dtarh'])
                    except InitialBorderDomin.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"InitialBorderDomin with pk {fields['dtarh']} not found")
                        )
                
                # Create new InitialBorderAttachmentDomain
                new_instance = InitialBorderAttachmentDomain.objects.create(
                    code=fields.get('code'),
                    name=fields.get('name', ''),
                    category=fields.get('category', ''),
                    dinitialborder=dinitialborder_instance
                )
                
                created_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f"Created InitialBorderAttachmentDomain: {new_instance.name} (code: {new_instance.code}, old pk: {old_pk})")
                )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"Error processing record {item.get('pk')}: {str(e)}")
                )
        
        # Print summary
        self.stdout.write(self.style.SUCCESS('\n=== Transfer Summary ==='))
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))