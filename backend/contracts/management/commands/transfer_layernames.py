import json
import os
from django.core.management.base import BaseCommand
from contracts.models.models import LayersNames, ContractDomin


class Command(BaseCommand):
    help = 'Transfer old Layers data to new LayersNames model, replicating for all ContractDomins'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to the JSON file containing old Layers data'
        )
        parser.add_argument(
            '--source-dtyp',
            type=int,
            required=True,
            help='The old dtyp_id to use as source template'
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
                content = content[json_start:]
            
            return json.loads(content)

    def handle(self, *args, **options):
        json_file = options['json_file']
        source_dtyp = options['source_dtyp']
        
        data = self.load_json(json_file)
        if not data:
            return
        
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(data)} layer records from {json_file}'))
        
        # Filter records with the specified dtyp_id
        source_layers = [item for item in data if item['fields'].get('dtyp_id') == source_dtyp]
        
        if not source_layers:
            self.stdout.write(self.style.ERROR(f'No layers found with dtyp_id={source_dtyp}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {len(source_layers)} layers with dtyp_id={source_dtyp}'))
        
        # Get all ContractDomins in new database
        contract_domins = ContractDomin.objects.all()
        
        if not contract_domins.exists():
            self.stdout.write(self.style.ERROR('No ContractDomins found in database'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {contract_domins.count()} ContractDomins'))
        
        # Statistics
        created_count = 0
        error_count = 0
        
        # For each ContractDomin, create all the layer definitions
        for contract_domin in contract_domins:
            self.stdout.write(self.style.SUCCESS(f'\nCreating layers for ContractDomin: {contract_domin.title}'))
            
            for item in source_layers:
                try:
                    fields = item['fields']
                    old_pk = item['pk']
                    
                    # Create LayersNames for this ContractDomin
                    new_layer = LayersNames.objects.create(
                        dtyp=contract_domin,
                        lyrgroup_en=fields.get('lyrgroup_en'),
                        lyrgroup_fa=fields.get('lyrgroup_fa'),
                        layername_en=fields.get('layername_en'),
                        layername_fa=fields.get('layername_fa'),
                        geometrytype=fields.get('geometrytype')
                    )
                    
                    created_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"  Created LayersNames: {new_layer.layername_fa} (from old pk: {old_pk})")
                    )
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"  Error creating layer from {item.get('pk')}: {str(e)}")
                    )
        
        # Print summary
        self.stdout.write(self.style.SUCCESS('\n=== Transfer Summary ==='))
        self.stdout.write(self.style.SUCCESS(f'Source layers used: {len(source_layers)}'))
        self.stdout.write(self.style.SUCCESS(f'ContractDomins: {contract_domins.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Total LayersNames created: {created_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))