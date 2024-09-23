import pandas as pd
from django.core.management.base import BaseCommand
from articles.models import Article
import qrcode
from django.conf import settings
import os
from django.urls import reverse
from datetime import datetime
import re

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str,)

    def handle(self, *args, **kwargs):
        excel_file = kwargs['excel_file']
        
        if not os.path.exists(excel_file):
            self.stderr.write(self.style.ERROR(f'Le fichier {excel_file} n\'existe pas.'))
            return

        try:
            df = pd.read_excel(excel_file)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Erreur lors de la lecture du fichier Excel : {e}'))
            return

        df.columns = [col.lower() for col in df.columns]

        required_columns = {'designation', 'qte', 'date acquisition', 'famille', 'emplacement', 'marque', 'model', 'prefixe'}
        if not required_columns.issubset(set(df.columns)):
            self.stderr.write(self.style.ERROR(f'Le fichier Excel doit contenir les colonnes suivantes : {required_columns}'))
            return

        for index, row in df.iterrows():
            designation = row['designation']
            qte = row['qte']
            date_acquisition_raw = row['date acquisition']
            famille = row['famille']
            emplacement = row['emplacement']
            marque = row['marque']
            model = row['model']
            prefixe = row['prefixe']

            date_acquisition_parsed = self.extract_date(date_acquisition_raw, designation)
            if not date_acquisition_parsed:
                self.stderr.write(self.style.ERROR(f'Article "{designation}" ignoré en raison d\'un format de date invalide.'))
                continue

            article, created = Article.objects.get_or_create(
                designation=designation,
                qte=qte,
                date_acquisition=date_acquisition_parsed,
                famille=famille,
                emplacement=emplacement,
                marque=marque,
                model=model,
                prefixe=prefixe
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Article "{designation}" créé.'))
            else:
                self.stdout.write(self.style.WARNING(f'Article "{designation}" déjà existant.'))

            site_url = 'http://127.0.0.1:8000'
            try:
                detail_url = site_url + reverse('article-detail', args=[article.id])
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Erreur lors de la génération de l\'URL pour "{designation}": {e}'))
                continue

            qr_data = detail_url

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            qr_code_filename = f'article_{article.id}.png'
            qr_code_path = os.path.join('qr_codes', qr_code_filename)
            full_qr_code_path = os.path.join(settings.MEDIA_ROOT, qr_code_path)

            os.makedirs(os.path.dirname(full_qr_code_path), exist_ok=True)

            img.save(full_qr_code_path)

            article.qr_code = qr_code_path
            article.save()

            self.stdout.write(self.style.SUCCESS(f'QR code généré pour "{designation}" avec URL : {detail_url}'))

        self.stdout.write(self.style.SUCCESS('Importation terminée.'))

    def extract_date(self, date_str, designation):
       
        if pd.isna(date_str):
            self.stderr.write(self.style.ERROR(f'Article "{designation}" a une valeur de date acquisition manquante.'))
            return None

        if isinstance(date_str, datetime):
            return date_str.date()

        if isinstance(date_str, str):
            match = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', date_str)
            if match:
                day, month, year = match.groups()
                try:
                    return datetime.strptime(f'{day}/{month}/{year}', '%d/%m/%Y').date()
                except ValueError:
                    self.stderr.write(self.style.ERROR(f'Article "{designation}" a une date invalide : {date_str}.'))
                    return None
            else:
                self.stderr.write(self.style.ERROR(f'Article "{designation}" n\'a pas de date valide dans : {date_str}.'))
                return None

        self.stderr.write(self.style.ERROR(f'Article "{designation}" a un type de date acquisition inconnu : {date_str}.'))
        return None
