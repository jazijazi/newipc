import json
import os
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry
from contracts.models.models import Contract, ContractDomin, ContractBorder
from common.models import Company
from initialborders.models.models import InitialBorder


class Command(BaseCommand):
    help = 'Transfer old Gharardad, Project, and ProjectGharar data to new Contract and ContractBorder models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--gharardad',
            type=str,
            required=True,
            help='Path to gharardad.json'
        )
        parser.add_argument(
            '--project',
            type=str,
            required=True,
            help='Path to project.json'
        )
        parser.add_argument(
            '--prjgharar',
            type=str,
            required=True,
            help='Path to prjgharar.json'
        )
        parser.add_argument(
            '--tarhs',
            type=str,
            required=True,
            help='Path to tarhs.json (needed to map old Tarh PKs to new InitialBorder)'
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
        # Load all JSON files
        self.stdout.write(self.style.SUCCESS('Loading JSON files...'))
        
        gharardad_data = self.load_json(options['gharardad'])
        project_data = self.load_json(options['project'])
        prjgharar_data = self.load_json(options['prjgharar'])
        tarhs_data = self.load_json(options['tarhs'])
        
        if not all([gharardad_data, project_data, prjgharar_data, tarhs_data]):
            self.stdout.write(self.style.ERROR('Failed to load one or more JSON files'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(gharardad_data)} contracts'))
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(project_data)} projects'))
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(prjgharar_data)} project-contract relations'))
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(tarhs_data)} tarhs'))
        
        # Statistics
        contract_created = 0
        contract_errors = 0
        contractborder_created = 0
        contractborder_errors = 0
        skipped_null_relations = 0
        skipped_no_initborder = 0
        skipped_no_border = 0
        
        # Step 0: Create mapping of old Tarh PKs to new InitialBorder titles
        self.stdout.write(self.style.SUCCESS('\n=== Step 0: Creating Tarh to InitialBorder mapping ==='))
        tarh_to_initborder = {}
        for item in tarhs_data:
            old_tarh_pk = item['pk']
            title = item['fields'].get('titletarh', '')
            
            # Find InitialBorder by title
            try:
                initborder = InitialBorder.objects.get(title=title)
                tarh_to_initborder[old_tarh_pk] = initborder
                self.stdout.write(self.style.SUCCESS(f"Mapped Tarh {old_tarh_pk} -> InitialBorder {initborder.pk} ({title})"))
            except InitialBorder.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"No InitialBorder found for Tarh {old_tarh_pk} ({title})"))
            except InitialBorder.MultipleObjectsReturned:
                self.stdout.write(self.style.WARNING(f"Multiple InitialBorders found for title: {title}"))
        
        self.stdout.write(self.style.SUCCESS(f'Mapped {len(tarh_to_initborder)} Tarhs to InitialBorders'))
        
        # Step 1: Create mapping of old project PKs to their data
        self.stdout.write(self.style.SUCCESS('\n=== Step 1: Creating project mapping ==='))
        project_map = {}
        for item in project_data:
            project_map[item['pk']] = item['fields']
        
        # Step 2: Transfer Gharardad to Contract
        self.stdout.write(self.style.SUCCESS('\n=== Step 2: Transferring Gharardad to Contract ==='))
        gharardad_to_contract = {}  # Map old Gharardad PK to new Contract instance
        
        for item in gharardad_data:
            try:
                fields = item['fields']
                old_pk = item['pk']
                
                # Get ContractDomin
                dtyp_instance = None
                if fields.get('dtyp'):
                    try:
                        dtyp_instance = ContractDomin.objects.get(pk=fields['dtyp'])
                    except ContractDomin.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"ContractDomin with pk {fields['dtyp']} not found")
                        )
                
                # Create Contract (without M2M companies for now)
                new_contract = Contract.objects.create(
                    title=fields.get('titlegh', ''),
                    dtyp=dtyp_instance,
                    number=fields.get('ghararNo'),
                    start_date=fields.get('startprj'),
                    end_date=fields.get('endprj'),
                    progress=fields.get('pishraft', 0),
                    is_completed=fields.get('khatemeh', False),
                    department=fields.get('department'),
                    elhaghye=fields.get('elhaghye', False),
                    mablagh=fields.get('mablagh'),
                    mablaghe_elhaghye=fields.get('mablaghe_elhaghye'),
                    tarikh_elhaghye=fields.get('tarikh_elhaghye')
                )
                
                gharardad_to_contract[old_pk] = new_contract
                contract_created += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f"Created Contract: {new_contract.title} (old pk: {old_pk})")
                )
                
                # Add M2M companies
                if fields.get('sherkatejraei'):
                    for company_pk in fields['sherkatejraei']:
                        try:
                            company = Company.objects.get(pk=company_pk)
                            new_contract.company.add(company)
                        except Company.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f"Company with pk {company_pk} not found")
                            )
                
            except Exception as e:
                contract_errors += 1
                self.stdout.write(
                    self.style.ERROR(f"Error creating Contract from {item.get('pk')}: {str(e)}")
                )
        
        # Step 3: Transfer ProjectGharar to ContractBorder
        self.stdout.write(self.style.SUCCESS('\n=== Step 3: Transferring ProjectGharar to ContractBorder ==='))
        
        for item in prjgharar_data:
            try:
                fields = item['fields']
                project_pk = fields.get('project')
                gharardad_pk = fields.get('gharardad')
                
                # Skip if either is null
                if not project_pk or not gharardad_pk:
                    skipped_null_relations += 1
                    continue
                
                # Get the new Contract
                if gharardad_pk not in gharardad_to_contract:
                    self.stdout.write(
                        self.style.WARNING(f"Contract not found for gharardad pk {gharardad_pk}")
                    )
                    continue
                
                new_contract = gharardad_to_contract[gharardad_pk]
                
                # Get old Project data
                if project_pk not in project_map:
                    self.stdout.write(
                        self.style.WARNING(f"Project pk {project_pk} not found in project data")
                    )
                    continue
                
                project_fields = project_map[project_pk]
                
                # Get InitialBorder from old Tarh FK using our mapping
                initborder_instance = None
                old_tarh_pk = project_fields.get('rtarh')
                if old_tarh_pk:
                    initborder_instance = tarh_to_initborder.get(old_tarh_pk)
                    if not initborder_instance:
                        self.stdout.write(
                            self.style.WARNING(f"No InitialBorder mapping for old Tarh pk {old_tarh_pk}")
                        )
                
                if not initborder_instance:
                    skipped_no_initborder += 1
                    continue
                
                # Parse border
                border_geom = None
                if project_fields.get('border'):
                    border_geom = GEOSGeometry(project_fields['border'])
                
                if not border_geom:
                    skipped_no_border += 1
                    continue
                
                # Map scale
                scale_value = None
                if project_fields.get('scale'):
                    scale_map = {
                        '1:250000': 250000,
                        '1:100000': 100000,
                        '1:50000': 50000,
                        '1:25000': 25000,
                        '1:10000': 10000,
                        '1:5000': 5000,
                        '1:2000': 2000,
                        '1:1000': 1000,
                        '1:500': 500,
                        '1:<500': 250
                    }
                    scale_value = scale_map.get(project_fields['scale'])
                
                # Create ContractBorder
                new_contractborder = ContractBorder.objects.create(
                    title=project_fields.get('titleprj', ''),
                    scale=scale_value,
                    border=border_geom,
                    contract=new_contract,
                    initborder=initborder_instance
                )
                
                contractborder_created += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f"Created ContractBorder: {new_contractborder.title}")
                )
                
            except Exception as e:
                contractborder_errors += 1
                self.stdout.write(
                    self.style.ERROR(f"Error creating ContractBorder from {item.get('pk')}: {str(e)}")
                )
        
        # Print summary
        self.stdout.write(self.style.SUCCESS('\n=== Transfer Summary ==='))
        self.stdout.write(self.style.SUCCESS(f'Contracts created: {contract_created}'))
        self.stdout.write(self.style.ERROR(f'Contract errors: {contract_errors}'))
        self.stdout.write(self.style.SUCCESS(f'ContractBorders created: {contractborder_created}'))
        self.stdout.write(self.style.ERROR(f'ContractBorder errors: {contractborder_errors}'))
        self.stdout.write(self.style.WARNING(f'Skipped (null relations): {skipped_null_relations}'))
        self.stdout.write(self.style.WARNING(f'Skipped (no InitialBorder): {skipped_no_initborder}'))
        self.stdout.write(self.style.WARNING(f'Skipped (no border geometry): {skipped_no_border}'))