import uuid
from typing import cast, Dict, Any
from django.db.models import Count, Sum, Q, F, Case, When, DecimalField, ExpressionWrapper, FloatField , BigIntegerField
from django.db.models.functions import Coalesce
from django.core.validators import FileExtensionValidator
from django.contrib.gis.db.models.functions import Area, Transform
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

from layers.utils import get_model_from_string
from layers.apps import LayersConfig

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
from layers.models.models import LayersNames

class ReportLayers(APIView):
    # permission is dynamic

    def get(self, request: Request) -> Response:
        try:
            result = {
                "geochemistry_point": self._get_geochemistry_point_report(),
                "geology_and_topo": self._get_geology_topo_report(),
                "drilling": self._get_drilling_report()
            }
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error in ReportLayers.get: {e}")
            return Response(
                {"detail": "خطا در گزارش لایه ها"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def _get_geochemistry_point_report(self) -> dict:
        """
        Generate report for geochemistry point layers.
        
        Returns:
            dict: Report containing count statistics for geochemistry points
        """
        layers = LayersNames.objects.filter(
            dtyp__code=11,
            lyrgroup_en="Geochemistry",
            geometrytype="point"
        )
        
        total_count = 0
        by_layer = []
        
        for layer_name in layers:
            model = get_model_from_string(
                model_app_label=LayersConfig.name,
                model_class_name=layer_name.layername_en
            )
            
            if model is None:
                continue
            
            count = model.objects.count()
            total_count += count
            
            by_layer.append({
                "count": count,
                "layername_fa": layer_name.layername_fa
            })
        
        return {
            "bylayer": by_layer,
            "message": "نمونه‌ برداری  به تعداد",
            "help": "همه گروه ژیوشیمی که point هستند و نتیجه به صورت نام فارسی جدول و تعداد رکورد",
            "all": total_count
        }
    
    def _get_geology_topo_report(self) -> dict:
        """
        Generate report for geology and topography layers (Rck_Typ_Area_Pg).
        
        Returns:
            dict: Report containing area statistics in km²
        """
        layers = LayersNames.objects.filter(
            dtyp__code=11,
            layername_en="Rck_Typ_Area_Pg",
            geometrytype="fill"
        )
        
        total_area = 0
        by_layer = []
        
        for layer_name in layers:
            model = get_model_from_string(
                model_app_label=LayersConfig.name,
                model_class_name=layer_name.layername_en
            )
            
            if model is None:
                continue
            
            area_result = model.objects.aggregate(total=Sum(Area('border')))
            area = round(area_result['total'].sq_km, 7) if area_result['total'] else 0
            
            total_area += area
            
            by_layer.append({
                "area": area,
                "layername_fa": layer_name.layername_fa,
                "geometrytype":layer_name.geometrytype, 
            })
        
        return {
            "bylayer": by_layer,
            "message": "زمین شناسی و توپوگرافی به هکتار",
            "help": "لایه Rck_Typ_Area_Pg مجموع مساحت همه عارضه ها",
            "all": total_area
        }

    def _get_drilling_report(self) -> dict:
        """
        Generate report for drilling layers.
        
        Returns:
            dict: Report containing depth statistics in meters
        """
        selected_layers_names = [
            "Extraction_Operation_Drilling_Pg",
            "Extraction_Operation_Drilling_Pl",
            "Extraction_Operation_Drilling_Pt"
            ]
        layers = LayersNames.objects.filter(
            dtyp__code=11,
            layername_en__in=selected_layers_names
        )
        
        total_depth = 0
        by_layer = []
        
        for layer_name in layers:
            model = get_model_from_string(
                model_app_label=LayersConfig.name,
                model_class_name=layer_name.layername_en
            )
            
            if model is None:
                continue
            
            depth_result = model.objects.aggregate(total=Sum('depth'))
            depth = depth_result['total'] or 0
            
            total_depth += depth
            
            by_layer.append({
                "depth": depth,
                "layername_fa": layer_name.layername_fa,
                "geometrytype":layer_name.geometrytype, 
            })
        
        return {
            "bylayer": by_layer,
            "message": "میزان حفاری به متراژ",
            "help": "مجموع فیلد depth همه لایه های Extraction_Operation_Drilling_Pg Extraction_Operation_Drilling_Pl Extraction_Operation_Drilling_Pt",
            "all": total_depth
        }