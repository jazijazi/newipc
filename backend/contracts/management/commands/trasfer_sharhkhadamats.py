import json
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from contracts.models.models import ShrhBase, ShrhLayer, Contract, ContractBorder, LayersNames
from accounts.models import User


class Command(BaseCommand):
    help = 'Transfer old Sharhkadamat data to new ShrhBase and ShrhLayer models'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to the JSON file containing old Sharhkadamat data'
        )
        parser.add_argument(
            '--prjgharar',
            type=str,
            required=True,
            help='Path to prjgharar.json'
        )
        parser.add_argument(
            '--gharardad',
            type=str,
            required=True,
            help='Path to gharardad.json (needed to map contracts)'
        )
        parser.add_argument(
            '--project',
            type=str,
            required=True,
            help='Path to project.json (needed to map contractborders)'
        )
        parser.add_argument(
            '--layernames',
            type=str,
            required=True,
            help='Path to layernames.json (old Layers data)'
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
        prjgharar_file = options['prjgharar']
        gharardad_file = options['gharardad']
        project_file = options['project']
        layernames_file = options['layernames']
        
        # Load all data
        sharhkadamat_data = self.load_json(json_file)
        prjgharar_data = self.load_json(prjgharar_file)
        gharardad_data = self.load_json(gharardad_file)
        project_data = self.load_json(project_file)
        layernames_data = self.load_json(layernames_file)
        
        if not all([sharhkadamat_data, prjgharar_data, gharardad_data, project_data, layernames_data]):
            self.stdout.write(self.style.ERROR('Failed to load one or more JSON files'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(sharhkadamat_data)} sharhkadamat records'))
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(prjgharar_data)} prjgharar records'))
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(gharardad_data)} gharardad records'))
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(project_data)} project records'))
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(layernames_data)} layernames records'))
        
        # Statistics
        shrhbase_created = 0
        shrhlayer_created = 0
        skipped_count = 0
        error_count = 0
        
        # Step 1: Create mapping from old gharardad title to new Contract
        self.stdout.write(self.style.SUCCESS('\n=== Step 1: Creating gharardad to Contract mapping ==='))
        gharardad_title_to_contract = {}
        
        for item in gharardad_data:
            old_gharardad_pk = item['pk']
            titlegh = item['fields'].get('titlegh', '')
            
            try:
                contract = Contract.objects.get(title=titlegh)
                gharardad_title_to_contract[old_gharardad_pk] = contract
                self.stdout.write(self.style.SUCCESS(f"Mapped gharardad {old_gharardad_pk} ({titlegh}) -> Contract {contract.pk}"))
            except Contract.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"No Contract found with title: {titlegh}"))
            except Contract.MultipleObjectsReturned:
                self.stdout.write(self.style.WARNING(f"Multiple Contracts found with title: {titlegh}"))
        
        # Step 2: Create mapping from old project title to new ContractBorder
        self.stdout.write(self.style.SUCCESS('\n=== Step 2: Creating project to ContractBorder mapping ==='))
        project_title_to_contractborder = {}
        
        for item in project_data:
            old_project_pk = item['pk']
            titleprj = item['fields'].get('titleprj', '')
            
            try:
                contractborder = ContractBorder.objects.get(title=titleprj)
                project_title_to_contractborder[old_project_pk] = contractborder
                self.stdout.write(self.style.SUCCESS(f"Mapped project {old_project_pk} ({titleprj}) -> ContractBorder {contractborder.pk}"))
            except ContractBorder.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"No ContractBorder found with title: {titleprj}"))
            except ContractBorder.MultipleObjectsReturned:
                self.stdout.write(self.style.WARNING(f"Multiple ContractBorders found with title: {titleprj}"))
        
        # Step 3: Create mapping from old layer PK to layer info (layername_en, dtyp_id)
        self.stdout.write(self.style.SUCCESS('\n=== Step 3: Creating old layer mapping ==='))
        old_layer_info = {}
        
        for item in layernames_data:
            old_layer_pk = item['pk']
            old_layer_info[old_layer_pk] = {
                'layername_en': item['fields'].get('layername_en'),
                'layername_fa': item['fields'].get('layername_fa'),
                'dtyp_id': item['fields'].get('dtyp_id')
            }
        
        # Step 4: Create mapping from prjgharar to Contract and ContractBorder
        self.stdout.write(self.style.SUCCESS('\n=== Step 4: Creating prjgharar mappings ==='))
        prjgharar_to_contract = {}
        prjgharar_to_contractborder = {}
        prjgharar_to_dtyp = {}
        
        for item in prjgharar_data:
            old_prjgharar_pk = item['pk']
            fields = item['fields']
            
            project_pk = fields.get('project')
            gharardad_pk = fields.get('gharardad')
            
            if not project_pk or not gharardad_pk:
                continue
            
            # Map to Contract
            if gharardad_pk in gharardad_title_to_contract:
                contract = gharardad_title_to_contract[gharardad_pk]
                prjgharar_to_contract[old_prjgharar_pk] = contract
                
                # Get dtyp from the contract
                if contract.dtyp:
                    prjgharar_to_dtyp[old_prjgharar_pk] = contract.dtyp
            
            # Map to ContractBorder
            if project_pk in project_title_to_contractborder:
                contractborder = project_title_to_contractborder[project_pk]
                prjgharar_to_contractborder[old_prjgharar_pk] = contractborder
        
        self.stdout.write(self.style.SUCCESS(f'Mapped {len(prjgharar_to_contract)} prjgharar to contracts'))
        self.stdout.write(self.style.SUCCESS(f'Mapped {len(prjgharar_to_contractborder)} prjgharar to contractborders'))
        
        # Step 5: Group Sharhkadamat by unique ShrhBase attributes
        self.stdout.write(self.style.SUCCESS('\n=== Step 5: Grouping Sharhkadamat for ShrhBase ==='))
        
        shrhbase_groups = {}
        
        for item in sharhkadamat_data:
            fields = item['fields']
            prjgharar_pk = fields.get('prjgharar')
            
            if not prjgharar_pk or prjgharar_pk not in prjgharar_to_contract:
                skipped_count += 1
                continue
            
            # Create unique key for grouping
            group_key = (
                prjgharar_pk,
                fields.get('title', ''),
                fields.get('vahed', ''),
                fields.get('hajm', 0),
                fields.get('gheymat', 0),
                fields.get('vazn', 0)
            )
            
            if group_key not in shrhbase_groups:
                shrhbase_groups[group_key] = []
            
            shrhbase_groups[group_key].append(item)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(shrhbase_groups)} unique ShrhBase groups'))
        
        # Step 6: Create ShrhBase and ShrhLayer records
        self.stdout.write(self.style.SUCCESS('\n=== Step 6: Creating ShrhBase and ShrhLayer records ==='))

        default_unit = ShrhBase.UNIT_CHOICES[0][0] if ShrhBase.UNIT_CHOICES else ''
        
        for group_key, items in shrhbase_groups.items():
            try:
                prjgharar_pk, title, vahed, hajm, gheymat, vazn = group_key
                
                contract = prjgharar_to_contract[prjgharar_pk]
                contractborder = prjgharar_to_contractborder.get(prjgharar_pk)
                contract_dtyp = prjgharar_to_dtyp.get(prjgharar_pk)
                
                if not contractborder:
                    self.stdout.write(self.style.WARNING(f"No contractborder for prjgharar {prjgharar_pk}, skipping"))
                    skipped_count += len(items)
                    continue
                
                # Get first item to extract common data
                first_item = items[0]
                fields = first_item['fields']

                # Validate unit against UNIT_CHOICES, use default if invalid
                valid_units = [choice[0] for choice in ShrhBase.UNIT_CHOICES]
                unit_to_use = vahed if vahed in valid_units else default_unit
                
                if vahed not in valid_units:
                    self.stdout.write(
                        self.style.WARNING(f"Invalid unit '{vahed}', using default '{default_unit}'")
                    )
                
                # Create ShrhBase
                shrh_base = ShrhBase.objects.create(
                    title=title,
                    unit=unit_to_use,
                    weight=vazn,
                    total_volume=int(hajm),
                    worked_volume=int(fields.get('hajmkarshde', 0)),
                    unit_price=gheymat,
                    contract=contract
                )
                
                shrhbase_created += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f"Created ShrhBase: {shrh_base.title} for contract {contract.title}")
                )
                
                # Create ShrhLayer for each item in this group
                for item in items:
                    try:
                        fields = item['fields']
                        old_layer_pk = fields.get('layer')
                        
                        if not old_layer_pk or old_layer_pk not in old_layer_info:
                            self.stdout.write(self.style.WARNING(f"Layer {old_layer_pk} not found in old data"))
                            continue
                        
                        layer_info = old_layer_info[old_layer_pk]
                        layername_en = layer_info['layername_en']
                        
                        # Find LayersNames by layername_en and contract's dtyp
                        try:
                            if contract_dtyp:
                                layer_name = LayersNames.objects.get(
                                    layername_en=layername_en,
                                    dtyp=contract_dtyp
                                )
                            else:
                                layer_name = LayersNames.objects.filter(
                                    layername_en=layername_en
                                ).first()
                                
                            if not layer_name:
                                self.stdout.write(
                                    self.style.WARNING(f"No LayersNames found for layername_en={layername_en}")
                                )
                                continue
                                
                        except LayersNames.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f"LayersNames not found: layername_en={layername_en}, dtyp={contract_dtyp}")
                            )
                            continue
                        except LayersNames.MultipleObjectsReturned:
                            # If multiple found, get the first one
                            layer_name = LayersNames.objects.filter(
                                layername_en=layername_en,
                                dtyp=contract_dtyp
                            ).first()
                        
                        # Get user if exists
                        verified_by = None
                        if fields.get('taeidnahaei_user'):
                            try:
                                verified_by = User.objects.get(pk=fields['taeidnahaei_user'])
                            except User.DoesNotExist:
                                pass

                        # Handle validation rules from old data
                        is_uploaded = fields.get('layer_bargozary', False)
                        is_verified = fields.get('taeidnahaei', False)
                        verified_at = fields.get('taeidnahaei_tarikh')

                        # Fix rule violations:
                        # Rule 1: If verified but not uploaded, set is_verified to False
                        if is_verified and not is_uploaded:
                            self.stdout.write(
                                self.style.WARNING(f"Layer was verified but not uploaded, setting is_verified=False")
                            )
                            is_verified = False
                            verified_by = None
                            verified_at = None
                        
                        # Rule 2: If verified but no verifier, set is_verified to False
                        if is_verified and not verified_by:
                            self.stdout.write(
                                self.style.WARNING(f"Layer was verified but no verifier found, setting is_verified=False")
                            )
                            is_verified = False
                            verified_at = None
                        
                        # Rule 3: If verified but no verified_at, set is_verified to False
                        if is_verified and not verified_at:
                            self.stdout.write(
                                self.style.WARNING(f"Layer was verified but no verified_at date, setting is_verified=False")
                            )
                            is_verified = False
                            verified_by = None
                        
                        # Rule 4: If not verified, clear verification data
                        if not is_verified:
                            verified_by = None
                            verified_at = None

                        
                        # Create ShrhLayer
                        shrh_layer = ShrhLayer.objects.create(
                            shrh_base=shrh_base,
                            layer_name=layer_name,
                            scale=None,
                            layer_weight=vazn,
                            layer_volume=int(hajm),
                            is_uploaded=is_uploaded,
                            last_uploaded_date=fields.get('tarikh_bargozary') if is_uploaded else None,
                            last_uploaded_by=None,
                            upload_count=1 if is_uploaded else 0,
                            is_verified=is_verified,
                            verified_by=verified_by,
                            verified_at=verified_at,
                            contractborder=contractborder
                        )
                        
                        shrhlayer_created += 1
                        
                        self.stdout.write(
                            self.style.SUCCESS(f"  Created ShrhLayer: {layer_name.layername_fa}")
                        )
                        
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f"  Error creating ShrhLayer: {str(e)}")
                        )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"Error creating ShrhBase for group: {str(e)}")
                )
        
        # Print summary
        self.stdout.write(self.style.SUCCESS('\n=== Transfer Summary ==='))
        self.stdout.write(self.style.SUCCESS(f'ShrhBase created: {shrhbase_created}'))
        self.stdout.write(self.style.SUCCESS(f'ShrhLayer created: {shrhlayer_created}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))