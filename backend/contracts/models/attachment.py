import os
from django.db import models
from django.conf import settings
from common.models import CustomModel

class ContractBorderAttachmentDomain(CustomModel):
    code = models.IntegerField(
        verbose_name="کد",
        unique=True
    )
    name_en = models.CharField(
        verbose_name="نام لاتین",
        max_length=100,
        unique=False,
        blank=False,
        null=False
    )
    name_fa = models.CharField(
        verbose_name="نام فارسی",
        max_length=100,
        unique=False,
        blank=False,null=False
    )
    typ = models.CharField(
        verbose_name="نوع",
        max_length=100,
        unique=False,
        blank=False,
        null=False
    )
    
    def __str__(self):
        return f'{self.name_en}_{self.code}'
    
    class Meta:
        verbose_name = "نوع پیوست محدوده قرارداد"
        verbose_name_plural = "انواع پیوست محدوده قرارداد"

def dynamic_upload_path(instance, filename):
    return f'contracts/achments/contract_{instance.contractborder.contract.pk}/contractborder_{instance.contractborder.id}/{filename}'

class ContractBorderAttachment(CustomModel):
    upload_date = models.DateTimeField(
        verbose_name="تاریخ ساخت",
        auto_now_add=True
    )
    writer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_contractborderattachment",
        blank=True,
        null=True
    ) 
    contractborder = models.ForeignKey(
        'ContractBorder',
        on_delete=models.CASCADE,
        blank=False,
        null=False,
        related_name='rcontractborderattachment'
    )
    dtyp = models.ForeignKey(
        'ContractBorderAttachmentDomain',
        on_delete=models.SET_NULL,
        related_name="dtyp_contractborderattachment",
        blank=True,
        null=True
    )
    file = models.FileField(
            verbose_name="فایل",
            blank=False,
            upload_to=dynamic_upload_path,
            max_length=500
        )
    
    def delete(self, *args, **kwargs):
        # Delete the file from the filesystem
        if self.file:
            try:
                if os.path.isfile(self.file.path):
                    os.remove(self.file.path)
                    # Remove empty directories
                    directory = os.path.dirname(self.file.path)
                    if os.path.exists(directory) and not os.listdir(directory):
                        os.rmdir(directory)
            except (OSError, ValueError):
                pass
        super().delete(*args, **kwargs)

    
    def __str__(self):
        return f'{self.pk} (border {self.contractborder.pk})'
    
    class Meta:
        verbose_name = "پیوست محودوه قرارداد"
        verbose_name_plural = "پیوست‌های محدوده قرارداد"