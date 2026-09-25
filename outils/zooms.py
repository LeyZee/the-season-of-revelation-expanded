"""zooms.py - trois gros plans de l'aperçu du monde à 8 px par hex (côte de Lyonesse, jonction Saison / Artois, Bois des
Rêves), pour l'article et pour Charles. Lecture seule."""
import os
import sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ICI = r"C:\TotalWar-CampaignMap\04-projets\saison-expanded\captures-article"
src = Image.open(os.path.join(ICI, "05_relief_monde_8px.jpg"))
ZOOMS = {"06a_zoom_cote_lyonesse.jpg": (0, 0, 1500, 1400),
         "06b_zoom_jonction_saison_artois.jpg": (880, 650, 2280, 1750),
         "06c_zoom_bois_des_reves.jpg": (1950, 4450, 3950, 6600)}
for nom, boite in ZOOMS.items():
    src.crop(boite).save(os.path.join(ICI, nom), quality=92)
    print(nom, boite)
