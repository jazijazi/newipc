"""
    All InitialBorder Metadata (base on InitialBorderDomin) goes here
"""

from django.db import models

class BaseInitialBorderMetadata(models.Model):
    # All initialborder shenasnameh inherit from this class
    rinitialborder = models.OneToOneField('InitialBorder' , on_delete=models.CASCADE, related_name='%(class)s_rinitialborder') #related_name must be unique
    # this fields are common in all Metadata's
    name        = models.CharField(verbose_name="نام",max_length=100, unique=False, blank=True, null=True)
    masahat     = models.FloatField(verbose_name="مساحت به کیلومترمربع",unique=False, blank=True, null=True)
    malekiyat   = models.CharField(verbose_name="مالکیت",max_length=100, unique=False, blank=True, null=True)
    ostan       = models.CharField(verbose_name="استان",max_length=100, unique=False, blank=True, null=True)
    shahrestan  = models.CharField(verbose_name="شهرستان",max_length=100, unique=False, blank=True, null=True)

    def __str__(self):
        return f"شناسنامه {self.rinitialborder.title}"

    class Meta:
        abstract = True


class InitialBorderMetadataPahneh(BaseInitialBorderMetadata):
    
    class Meta:
        verbose_name = "شناسنامه محدوده اولیه پهنه"
        verbose_name_plural = "شناسنامه محدوده اولیه پهنه"

class InitialBorderMetadataDarkhastekteshaf(BaseInitialBorderMetadata):
    cadastre      = models.CharField(verbose_name="شماره کاداستر",max_length=100, unique=False, blank=True, null=True)
    noemademadani = models.CharField(verbose_name="نوع ماده معدنی",max_length=100, unique=False, blank=True, null=True)
    organs        = models.CharField(verbose_name="ارگان های استعلام شونده",max_length=250, unique=False, blank=True, null=True)
    
    class Meta:
        verbose_name = "شناسنامه محدوده اولیه درخواست اکتشاف"
        verbose_name_plural = "شناسنامه محدوده اولیه درخواست اکتشاف"

class InitialBorderMetadataParvaneekteshaf(BaseInitialBorderMetadata):
    cadastre        = models.CharField(verbose_name="شماره کاداستر",max_length=100, unique=False, blank=True, null=True)
    noemademadani   = models.CharField(verbose_name="نوع ماده معدنی",max_length=100, unique=False, blank=True, null=True)
    shomareparvaneh = models.CharField(verbose_name="شماره پروانه",max_length=100, unique=False, blank=True, null=True)
    tarikhparvane   = models.DateField(verbose_name="تاریخ پروانه",auto_now=False,auto_now_add=False,null=True,blank=True)
    tarikhetebar    = models.DateField(verbose_name="تاریخ اعتبار",auto_now=False,auto_now_add=False,null=True,blank=True)
    
    class Meta:
        verbose_name = "شناسنامه محدوده اولیه پروانه اکتشاف"
        verbose_name_plural = "شناسنامه محدوده اولیه پروانه اکتشاف"

class InitialBorderMetadataGovahikashf(BaseInitialBorderMetadata):
    cadastre           = models.CharField(verbose_name="شماره کاداستر",max_length=100, unique=False, blank=True, null=True)
    noemademadani      = models.CharField(verbose_name="نوع ماده معدنی",max_length=100, unique=False, blank=True, null=True)
    shomareparvaneh    = models.CharField(verbose_name="شماره پروانه",max_length=100, unique=False, blank=True, null=True)
    tarikhparvane      = models.DateField(verbose_name="تاریخ پروانه",auto_now=False,auto_now_add=False,null=True,blank=True)
    tarietebargovahi   = models.DateField(verbose_name="تاریخ اعتبار گواهی",auto_now=False,auto_now_add=False,null=True,blank=True)
    zakhireehtemali    = models.FloatField(verbose_name="ذخیره احتمالی به تن",unique=False, blank=True, null=True)
    zakhireghatei      = models.FloatField(verbose_name="ذخیره قطعی به تن",unique=False, blank=True, null=True)
    ayarehad           = models.FloatField(verbose_name="عیار حد به درصد",unique=False, blank=True, null=True)
    ayaremeyangin      = models.FloatField(verbose_name="عیار میانگین به درصد",unique=False, blank=True, null=True)
    shomaregovahikashf = models.CharField(verbose_name="شماره گواهی کشف",max_length=100, unique=False, blank=True, null=True)
    tarikhsodurgivahikashf = models.DateField(verbose_name="تاریخ صدور گواهی کشف",auto_now=False,auto_now_add=False,null=True,blank=True)
        
    class Meta:
        verbose_name = "شناسنامه محدوده اولیه گواهی کشف"
        verbose_name_plural = "شناسنامه محدوده اولیه گواهی کشف"

class InitialBorderMetadataParvanebahrebardai(BaseInitialBorderMetadata):
    cadastre          = models.CharField(verbose_name="شماره کاداستر",max_length=100, unique=False, blank=True, null=True)
    noemademadani     = models.CharField(verbose_name="نوع ماده معدنی",max_length=100, unique=False, blank=True, null=True)
    shomareparvaneh   = models.CharField(verbose_name="شماره پروانه",max_length=100, unique=False, blank=True, null=True)
    tarikhparvane     = models.DateField(verbose_name="تاریخ پروانه",auto_now=False,auto_now_add=False,null=True,blank=True)
    tarietebarparvane = models.DateField(verbose_name="تاریخ اعتبار پروانه",auto_now=False,auto_now_add=False,null=True,blank=True)
    zakhireehtemali   = models.FloatField(verbose_name="ذخیره احتمالی به تن",unique=False, blank=True, null=True)
    zakhireghatei     = models.FloatField(verbose_name="ذخیره قطعی به تن",unique=False, blank=True, null=True)
    ayarehad          = models.FloatField(verbose_name="عیار حد به درصد",unique=False, blank=True, null=True)
    ayaremeyangin     = models.FloatField(verbose_name="عیار میانگین به درصد",unique=False, blank=True, null=True)
    estekhrajsaleyane = models.FloatField(verbose_name=" استخراج سالیانه به تن",unique=False, blank=True, null=True)
        
    class Meta:
        verbose_name = "شناسنامه محدوده اولیه پروانه بهره برداری"
        verbose_name_plural = "شناسنامه محدوده اولیه پروانه بهره برداری"

class InitialBorderMetadataPotansielyabi(BaseInitialBorderMetadata):
    noemademadani = models.CharField(verbose_name="نوع ماده معدنی",max_length=100, unique=False, blank=True, null=True)
        
    class Meta:
        verbose_name = "شناسنامه محدوده اولیه پتانسیل یابی"
        verbose_name_plural = "شناسنامه محدوده قانواولیهنی پتانسیل یابی"