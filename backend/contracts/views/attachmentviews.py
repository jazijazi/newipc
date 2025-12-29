import logging
from logs.utils import get_details_from_request

from django.core.validators import FileExtensionValidator

from rest_framework.response import Response
from rest_framework.request import Request

from rest_framework import serializers
from rest_framework.permissions import AllowAny

from common.pagination import CustomPagination

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.urls import reverse

from contracts.models.models import (
    ContractBorder,
)
from contracts.models.attachment import(
    ContractBorderAttachment,
    ContractBorderAttachmentDomain
)
from accounts.models import(
    User
)

delete_logger = logging.getLogger('delete_activity_logger')

class ContractBorderAttachmentDomainListApiView(APIView):
    """
        List Of ContractBorder Attachment Domain`s
    """

    class ContractBorderAttachmentDomainListOutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = ContractBorderAttachmentDomain
            fields = ['id' , 'code', 'name_en', 'name_fa', 'typ']

    class ContractBorderAttachmentDomainListInputSerializer(serializers.ModelSerializer):
        class Meta:
            model = ContractBorderAttachmentDomain
            fields = ['code', 'name_en', 'name_fa', 'typ'] 

    def get(self , request:Request) -> Response:
        try:
            all_contractborderattachmentdomain = ContractBorderAttachmentDomain.objects.all()
            paginator = CustomPagination()
            paginated_queryset = paginator.paginate_queryset(all_contractborderattachmentdomain, request)
            serializer = self.ContractBorderAttachmentDomainListOutputSerializer(paginated_queryset,many=True,context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در خواندن انواع پیوست های محدوده قرارداد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self , request:Request) -> Response:
        try:
            input_serializer = self.ContractBorderAttachmentDomainListInputSerializer(data=request.data)
            if input_serializer.is_valid():
                shrh_instance = input_serializer.save()
                output_serializer = self.ContractBorderAttachmentDomainListOutputSerializer(shrh_instance)
                return Response(output_serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در ساخت شرح خدمات"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ContractBorderAttachmentDomainDetailsApiView(APIView):
    class ContractBorderAttachmentDomainDetailsOutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = ContractBorderAttachmentDomain
            fields = ['id' , 'code', 'name_en', 'name_fa', 'typ']

    class ContractBorderAttachmentDomainDetailsInputSerializer(serializers.ModelSerializer):
        class Meta:
            model = ContractBorderAttachmentDomain
            fields = ['code', 'name_en', 'name_fa', 'typ'] 

    def get(self , request:Request , pk:int) -> Response:
        try:
            contractborderattachmentdomainـinstance = ContractBorderAttachmentDomain.objects.get(pk=pk)
            serializer = self.ContractBorderAttachmentDomainDetailsOutputSerializer(contractborderattachmentdomainـinstance)
            return Response(serializer.data , status=status.HTTP_200_OK)
        except ContractBorderAttachmentDomain.DoesNotExist:
            return Response({"detail": "نوع پیوست محدوده قراردادی با این آیدی یافت نشد"}, status=status.HTTP_404_NOT_FOUND) 
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در خواندن نوع پیوست محدوده قرارداد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

    def put(self , request:Request , pk:int) -> Response:
        try:
            contractborderattachmentdomain_instance = ContractBorderAttachmentDomain.objects.get(pk=pk)
            serializer = self.ContractBorderAttachmentDomainDetailsInputSerializer(
                contractborderattachmentdomain_instance, 
                data=request.data,
                partial=True
            )
            if serializer.is_valid():
                # Save the updated instance
                updated_instance = serializer.save()
                output_serializer = self.ContractBorderAttachmentDomainDetailsOutputSerializer(updated_instance)
                return Response(output_serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except ContractBorderAttachmentDomain.DoesNotExist:
            return Response({"detail": "نوع پیوست محدوده قراردادی با این آیدی یافت نشد"}, status=status.HTTP_404_NOT_FOUND) 
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در ویرایش نوع پیوست محدوده قرارداد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self , request:Request , pk:int) -> Response:
        try:
            contractborderattachmentdomainـinstance = ContractBorderAttachmentDomain.objects.get(pk=pk)
            contractborderattachmentdomainـinstance.delete()
            delete_logger.warning(f"حذف نوع پیوست محدوده قرارداد {contractborderattachmentdomainـinstance.name_fa}" , extra=get_details_from_request(request))
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ContractBorderAttachmentDomain.DoesNotExist:
            return Response({"detail": "نوع پیوست محدوده قراردادی با این آیدی یافت نشد"}, status=status.HTTP_404_NOT_FOUND) 
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در حذف نوع پیوست محدوده قرارداد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ContractBorderAttachmentListApiView(APIView):
    """
        GET: return all attachment of a contractborder
        POST: create new attachment of a contractborder

        check object-level
        if user is superuser has access 
        else return only thoes check user has access to it via
        shrhlayer -> contractborder
    """

    class ContractBorderAttachmentListOutputSerializer(serializers.ModelSerializer):
        class ContractBorderAttachmentListOutputSerializerUser(serializers.ModelSerializer): 
            class Meta:
                model = User
                fields = ['username' , 'first_name_fa' , 'last_name_fa']
        class ContractBorderAttachmentListOutputSerializerDtyp(serializers.ModelSerializer): 
            class Meta:
                model = ContractBorderAttachmentDomain
                fields = ['id' , 'code', 'name_en', 'name_fa', 'typ']

        writer = ContractBorderAttachmentListOutputSerializerUser()
        dtyp = ContractBorderAttachmentListOutputSerializerDtyp()

        class Meta:
            model = ContractBorderAttachment
            fields = ['id','upload_date','writer','contractborder','dtyp','file',]

    class ContractBorderAttachmentListInputSerializer(serializers.Serializer):
        file = serializers.FileField(required=True,allow_null=False)
        dtyp_attach = serializers.IntegerField(required=True,allow_null=False)

        def validate_dtyp_attach(self, value):
            try:
                dtyp_attach_instance = ContractBorderAttachmentDomain.objects.get(pk=value)
                return value
            except ContractBorderAttachmentDomain.DoesNotExist:
                raise serializers.ValidationError("نوع پیوست یافت نشد")


    def get(self , request:Request , contractborderid:str)-> Response :
        try:
            user : User = request.user
            contractborder_instance = ContractBorder.objects.get(pk=contractborderid)
            if not user.is_superuser and not user.has_contractborder_access(contractborder_instance):
                return Response({"detail": "کاربر به محدوده قرارداد دسترسی ندارد"},status=status.HTTP_403_FORBIDDEN)
            all_contractborderattachments = ContractBorderAttachment.objects.filter(contractborder=contractborder_instance)
            paginator = CustomPagination()
            paginated_queryset = paginator.paginate_queryset(all_contractborderattachments, request)
            serializer = self.ContractBorderAttachmentListOutputSerializer(paginated_queryset,many=True,context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        
        except ContractBorder.DoesNotExist:
            return Response({"detail": "محدوده قراردادی با این آیدی یافت نشد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در خواندن پیوست های این محدوده قرارداد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def post(self , request:Request , contractborderid:str)-> Response :
        try:
            user : User = request.user
            contractborder_instance = ContractBorder.objects.get(pk=contractborderid)
            if not user.is_superuser and not user.has_contractborder_access(contractborder_instance):
                return Response({"detail": "کاربر به محدوده قرارداد دسترسی ندارد"},status=status.HTTP_403_FORBIDDEN)
            serializer = self.ContractBorderAttachmentListInputSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors , status=status.HTTP_400_BAD_REQUEST)
            
            validated_data = serializer.validated_data

            dtyp_attach_instance = ContractBorderAttachmentDomain.objects.get(pk=validated_data['dtyp_attach'])

            contractborderattachment_instance = ContractBorderAttachment.objects.create(
                writer = request.user,
                contractborder = contractborder_instance,
                dtyp = dtyp_attach_instance,
                file = validated_data['file'],
            )

            output_serializer = self.ContractBorderAttachmentListOutputSerializer(contractborderattachment_instance,many=False,context={'request': request})
            return Response(output_serializer.data , status=status.HTTP_201_CREATED)
            
        except ContractBorderAttachmentDomain.DoesNotExist:
                raise serializers.ValidationError("نوع پیوست یافت نشد")
        except ContractBorder.DoesNotExist:
            return Response({"detail": "محدوده قراردادی با این آیدی یافت نشد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در ساخت پیوست برای این محدوده قرارداد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ContractBorderAttachmentDetailsApiView(APIView):
    """
        GET: return an attachment of a contractborder
        DELETE: delete an attachment of a contractborder

        check object-level
        if user is superuser has access 
        else return only thoes check user has access to it via
        shrhlayer -> contractborder
    """
    class ContractBorderAttachmentDetailsOutputSerializer(serializers.ModelSerializer):
        class ContractBorderAttachmentDetailsOutputSerializerUser(serializers.ModelSerializer): 
            class Meta:
                model = User
                fields = ['username' , 'first_name_fa' , 'last_name_fa']
        class ContractBorderAttachmentDetailsOutputSerializerDtyp(serializers.ModelSerializer): 
            class Meta:
                model = ContractBorderAttachmentDomain
                fields = ['id' , 'code', 'name_en', 'name_fa', 'typ']

        writer = ContractBorderAttachmentDetailsOutputSerializerUser()
        dtyp = ContractBorderAttachmentDetailsOutputSerializerDtyp()

        class Meta:
            model = ContractBorderAttachment
            fields = ['id','upload_date','writer','contractborder','dtyp','file',]

    def get(self , request:Request , contractborderattachmentid:int)-> Response :
        try:
            user : User = request.user
            contractborderattachment_instance = ContractBorderAttachment.objects.get(pk=contractborderattachmentid)
            if not user.is_superuser and not user.has_contractborder_access(contractborderattachment_instance.contractborder):
                return Response({"detail": "کاربر به محدوده قرارداد دسترسی ندارد"},status=status.HTTP_403_FORBIDDEN)
            serializer = self.ContractBorderAttachmentDetailsOutputSerializer(contractborderattachment_instance,many=False,context={'request': request})
            return Response(serializer.data , status=status.HTTP_200_OK)
        except ContractBorderAttachment.DoesNotExist:
            return Response({"detail": "پیوست محدوده قراردادی با این آیدی یافت نشد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در خواندن پیوست محدوده قرارداد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # def put ?????

    def delete(self , request:Request , contractborderattachmentid:int)-> Response :
        try:
            user : User = request.user
            contractborderattachment_instance = ContractBorderAttachment.objects.get(pk=contractborderattachmentid)
            if not user.is_superuser and not user.has_contractborder_access(contractborderattachment_instance.contractborder):
                return Response({"detail": "کاربر به محدوده قرارداد دسترسی ندارد"},status=status.HTTP_403_FORBIDDEN)
            contractborderattachment_instance.delete()
            delete_logger.warning(f"حذف پیوست محدوده قرارداد {contractborderattachment_instance.file.path}" , extra=get_details_from_request(request))
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ContractBorderAttachment.DoesNotExist:
            return Response({"detail": "پیوست محدوده قراردادی با این آیدی یافت نشد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در حذف پیوست محدوده قرارداد"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
