import uuid
from typing import cast, Dict, Any
from django.db.models import Count, Sum, Q, F, Case, When, DecimalField, ExpressionWrapper, FloatField , BigIntegerField
from django.db.models.functions import Coalesce
from django.core.validators import FileExtensionValidator
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import serializers
from rest_framework.permissions import AllowAny , IsAdminUser
from common.pagination import CustomPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.urls import reverse
from django.db import transaction
from django.contrib.gis.geos import MultiPolygon
from common.models import Company , Province
from accounts.models import User


from initialborders.models.models import (
    InitialBorder,
    InitialBorderDomin,
)
from contracts.models.models import (
    Contract,
    ContractDomin,
    ContractBorder,
    ShrhLayer,
    ShrhBase,
)

class ReportContracts(APIView):
    # permission is dynamic

    def get(self , request:Request) -> Response:
        try:
            user = request.user

            # Single query with all aggregations
            stats = Contract.objects.aggregate(
                # Counts
                completed_count=Count('id', filter=Q(is_completed=True)),
                not_completed_count=Count('id', filter=Q(is_completed=False)),
                
                # Sum of mablagh for all
                total_mablagh=Sum('mablagh'),
                total_mablaghe_elhaghye=Sum('mablaghe_elhaghye'),
                
                # Sum of mablagh for completed
                completed_mablagh=Sum('mablagh', filter=Q(is_completed=True)),
                completed_mablaghe_elhaghye=Sum('mablaghe_elhaghye', filter=Q(is_completed=True)),
                
                # Sum of mablagh for not completed
                not_completed_mablagh=Sum('mablagh', filter=Q(is_completed=False)),
                not_completed_mablaghe_elhaghye=Sum('mablaghe_elhaghye', filter=Q(is_completed=False)),
            )

            # Helper function to safely add nullable values
            def safe_sum(*values):
                return sum(v for v in values if v is not None)
            
            result = {
                "count": {
                    "is_completed": stats['completed_count'] or 0,
                    "is_not_completed": stats['not_completed_count'] or 0
                },
                "mablagh": {
                    "all": safe_sum(
                        stats['total_mablagh'], 
                        stats['total_mablaghe_elhaghye']
                    ),
                    "is_completed": safe_sum(
                        stats['completed_mablagh'], 
                        stats['completed_mablaghe_elhaghye']
                    ),
                    "is_not_completed": safe_sum(
                        stats['not_completed_mablagh'], 
                        stats['not_completed_mablaghe_elhaghye']
                    )
                }
            }
            
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response({"detail": "خطا در گزارش کلی قرارداد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ReportContractsByCompany(APIView):
    # permission is dynamic

    def get(self , request:Request) -> Response:
        try:
            user = request.user

            # Single query to get all companies with their contract statistics
            company_stats = Company.objects.annotate(
                # Count completed contracts
                completed_count=Count(
                    'rcompanycontracts',
                    filter=Q(rcompanycontracts__is_completed=True),
                    distinct=True
                ),
                # Count not completed contracts
                not_completed_count=Count(
                    'rcompanycontracts',
                    filter=Q(rcompanycontracts__is_completed=False),
                    distinct=True
                ),
                # Sum all mablagh
                total_mablagh=Sum('rcompanycontracts__mablagh'),
                total_mablaghe_elhaghye=Sum('rcompanycontracts__mablaghe_elhaghye'),
                
                # Sum completed mablagh
                completed_mablagh=Sum(
                    'rcompanycontracts__mablagh',
                    filter=Q(rcompanycontracts__is_completed=True)
                ),
                completed_mablaghe_elhaghye=Sum(
                    'rcompanycontracts__mablaghe_elhaghye',
                    filter=Q(rcompanycontracts__is_completed=True)
                ),
                
                # Sum not completed mablagh
                not_completed_mablagh=Sum(
                    'rcompanycontracts__mablagh',
                    filter=Q(rcompanycontracts__is_completed=False)
                ),
                not_completed_mablaghe_elhaghye=Sum(
                    'rcompanycontracts__mablaghe_elhaghye',
                    filter=Q(rcompanycontracts__is_completed=False)
                ),
            ).filter(
                # Only include companies that have at least one contract
                Q(completed_count__gt=0) | Q(not_completed_count__gt=0)
            ).values(
                'name',
                'typ',
                'completed_count',
                'not_completed_count',
                'total_mablagh',
                'total_mablaghe_elhaghye',
                'completed_mablagh',
                'completed_mablaghe_elhaghye',
                'not_completed_mablagh',
                'not_completed_mablaghe_elhaghye'
            ).order_by('name')

            
            # Helper function to safely add nullable values
            def safe_sum(*values):
                return sum(v for v in values if v is not None)
            
            # Build result list
            result = []
            for company in company_stats:
                result.append({
                    "company_name": company['name'],
                    "company_typ": company['typ'] or "",  # Handle None
                    "count": {
                        "is_completed": company['completed_count'] or 0,
                        "is_not_completed": company['not_completed_count'] or 0
                    },
                    "mablagh": {
                        "all": safe_sum(
                            company['total_mablagh'],
                            company['total_mablaghe_elhaghye']
                        ),
                        "is_completed": safe_sum(
                            company['completed_mablagh'],
                            company['completed_mablaghe_elhaghye']
                        ),
                        "is_not_completed": safe_sum(
                            company['not_completed_mablagh'],
                            company['not_completed_mablaghe_elhaghye']
                        )
                    }
                })
            
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response({"detail": "خطا در گزارش قرارداد بر اساس شرکت"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
      
class ReportContractsBySharh(APIView):
    # permission is dynamic

    def get(self, request: Request) -> Response:
        try:
            user = request.user
            
            # Query contracts with aggregated ShrhBase statistics
            contracts_stats = Contract.objects.annotate(
                # Count of shrh items
                shrh_count=Count('shrh_items'),
                
                # Total volumes
                total_volume_sum=Coalesce(Sum('shrh_items__total_volume'), 0),
                worked_volume_sum=Coalesce(Sum('shrh_items__worked_volume'), 0),
                
                # Calculate remaining volume
                remaining_volume_sum=ExpressionWrapper(
                    F('total_volume_sum') - F('worked_volume_sum'),
                    output_field=FloatField()
                ),
                
                # Total prices (unit_price * total_volume)
                total_price_sum=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F('shrh_items__unit_price') * F('shrh_items__total_volume'),
                            output_field=BigIntegerField()
                        )
                    ),
                    0
                ),
                
                # Completed prices (unit_price * worked_volume)
                completed_price_sum=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F('shrh_items__unit_price') * F('shrh_items__worked_volume'),
                            output_field=BigIntegerField()
                        )
                    ),
                    0
                ),
                
                # Sum of weights
                total_weight=Coalesce(Sum('shrh_items__weight'), 0),
                
            ).filter(
                shrh_count__gt=0  # Only contracts with at least one shrh item
            ).values(
                'id',
                'title',
                'number',
                'is_completed',
                'progress',
                'shrh_count',
                'total_volume_sum',
                'worked_volume_sum',
                'remaining_volume_sum',
                'total_price_sum',
                'completed_price_sum',
                'total_weight'
            ).order_by('title')
            
            # Build result list
            result = []
            for contract in contracts_stats:
                # Calculate completion percentage from volumes
                if contract['total_volume_sum'] > 0:
                    volume_completion_percentage = min(
                        (contract['worked_volume_sum'] / contract['total_volume_sum']) * 100,
                        100
                    )
                else:
                    volume_completion_percentage = 0
                
                # Calculate price completion percentage
                if contract['total_price_sum'] > 0:
                    price_completion_percentage = min(
                        (float(contract['completed_price_sum']) / float(contract['total_price_sum'])) * 100,
                        100
                    )
                else:
                    price_completion_percentage = 0
                
                # Remaining price
                remaining_price = max(
                    float(contract['total_price_sum']) - float(contract['completed_price_sum']),
                    0
                )
                
                result.append({
                    "contract_id": str(contract['id']),
                    "contract_title": contract['title'],
                    "contract_number": contract['number'] or "",
                    "is_completed": contract['is_completed'],
                    "contract_progress": contract['progress'],
                    "shrh_statistics": {
                        "total_items": contract['shrh_count'],
                        "total_weight": contract['total_weight'],
                        "volume": {
                            "total": contract['total_volume_sum'],
                            "worked": contract['worked_volume_sum'],
                            "remaining": max(contract['remaining_volume_sum'], 0),
                            "completion_percentage": round(volume_completion_percentage, 2)
                        },
                        "price": {
                            "total": int(contract['total_price_sum']),
                            "completed": int(contract['completed_price_sum']),
                            "remaining": int(remaining_price),
                            "completion_percentage": round(price_completion_percentage, 2)
                        }
                    }
                })
            
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response(
                {"detail": "خطا در گزارش قراردادها بر اساس شرح خدمات"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        





