from django.db import models
import qrcode
from django.conf import settings
import os
from django.urls import reverse

class Article(models.Model):
    designation = models.CharField(max_length=255)
    qte = models.IntegerField()
    date_acquisition = models.CharField(max_length=255, blank=True, null=True) 
    famille = models.CharField(max_length=255)
    emplacement = models.CharField(max_length=255)
    marque = models.CharField(max_length=255)
    model = models.CharField(max_length=255)
    prefixe = models.CharField(max_length=50)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def __str__(self):
        return self.designation

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.qr_code:
            site_url = 'http://127.0.0.1:8000'  
            try:
                detail_url = site_url + reverse('article-detail', args=[self.id])
            except Exception as e:
                print(f"Erreur lors de la génération de l'URL pour QR code: {e}")
                detail_url = site_url

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(detail_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            qr_code_filename = f'article_{self.id}.png'
            qr_code_path = os.path.join('qr_codes', qr_code_filename)
            full_qr_code_path = os.path.join(settings.MEDIA_ROOT, qr_code_path)

            os.makedirs(os.path.dirname(full_qr_code_path), exist_ok=True)

            img.save(full_qr_code_path)

            self.qr_code = qr_code_path

            super().save(update_fields=['qr_code'])
