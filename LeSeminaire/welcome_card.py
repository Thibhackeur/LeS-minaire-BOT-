"""
Module de génération de cartes de bienvenue artistiques et animées.
Permet de créer des cartes de bienvenue personnalisées pour les nouveaux membres 
du serveur Le Séminaire avec un style artistique et des animations.
"""

import os
import io
import random
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance, ImageColor
import imageio
import logging
import discord
import tempfile

# Configuration du logger
logger = logging.getLogger('welcome_card')

# Couleurs artistiques (palette Le Séminaire)
COLORS = {
    'primary': "#7289DA",  # Bleu Discord
    'secondary': "#FF9966",  # Orange artistique
    'accent': "#66CCFF",  # Bleu ciel
    'dark': "#2C2F33",  # Gris foncé
    'light': "#FFFFFF",  # Blanc
    'background': "#23272A",  # Fond sombre
    'highlight': "#FFD700",  # Or / Jaune vif
    'creative': "#9B59B6",  # Violet créatif
    'music': "#E74C3C",  # Rouge musique
    'visual': "#3498DB",  # Bleu visuel
}

# Styles artistiques disponibles
STYLES = [
    'musical',   # Style musical avec des notes et des ondes sonores
    'visual',    # Style visuel avec des éléments graphiques
    'minimal',   # Style minimaliste épuré
    'vibrant',   # Style coloré et vibrant
    'retro',     # Style rétro/vintage
    'neon',      # Style néon avec des couleurs fluorescentes
    'abstract',  # Style abstrait avec des formes géométriques
    'pixel',     # Style pixel art rétro-gaming
    'gradient',  # Style avec dégradés de couleurs
    'paint',     # Style peinture artistique
]

# Effets d'animation
ANIMATIONS = [
    'fade_in',       # Fondu à l'ouverture
    'slide_in',      # Glissement latéral
    'pulse',         # Pulsation des éléments
    'particles',     # Particules artistiques
    'color_shift',   # Changement progressif de couleurs
    'bounce',        # Effet de rebond
    'rotate',        # Rotation d'éléments
    'glitch',        # Effet glitch numérique
    'typewriter',    # Texte qui s'écrit progressivement
    'fireworks',     # Explosion de particules
    'wave',          # Effet d'onde qui se propage
    'sparkle',       # Scintillement d'éléments
]

# Chemins des ressources
ASSETS_DIR = 'assets/welcome'
FONTS_DIR = 'assets/welcome/fonts'

# Création du dossier assets s'il n'existe pas
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

class WelcomeCardGenerator:
    """
    Générateur de cartes de bienvenue personnalisées et animées.
    """
    
    def __init__(self):
        """Initialise le générateur de cartes de bienvenue."""
        self.default_width = 800
        self.default_height = 400
        self.frame_count = 15
        self.avatar_size = 128
        
        # Charger ou télécharger les polices si nécessaire
        self._ensure_font_resources()
        
    def _ensure_font_resources(self):
        """Vérifie que les ressources de polices sont disponibles, sinon les télécharge."""
        # Liste des polices à utiliser avec leurs URLs
        fonts = {
            'main': {
                'url': 'https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Bold.ttf',
                'path': os.path.join(FONTS_DIR, 'Montserrat-Bold.ttf')
            },
            'secondary': {
                'url': 'https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf',
                'path': os.path.join(FONTS_DIR, 'Poppins-Regular.ttf')
            },
            'accent': {
                'url': 'https://github.com/google/fonts/raw/main/ofl/dancingscript/DancingScript%5Bwght%5D.ttf',
                'path': os.path.join(FONTS_DIR, 'DancingScript.ttf')
            }
        }
        
        # Vérifier et télécharger chaque police si nécessaire
        for font_name, font_info in fonts.items():
            if not os.path.exists(font_info['path']):
                try:
                    logger.info(f"Téléchargement de la police {font_name}...")
                    response = requests.get(font_info['url'])
                    response.raise_for_status()
                    
                    with open(font_info['path'], 'wb') as f:
                        f.write(response.content)
                    
                    logger.info(f"Police {font_name} téléchargée avec succès.")
                except Exception as e:
                    logger.error(f"Erreur lors du téléchargement de la police {font_name}: {e}")
    
    async def _get_avatar_image(self, member):
        """
        Récupère l'image de profil du membre et la prépare pour l'utilisation dans la carte.
        
        Args:
            member: Le membre Discord dont il faut récupérer l'avatar
            
        Returns:
            Image PIL préparée avec l'avatar ou une image par défaut
        """
        avatar_url = member.display_avatar.url
        
        try:
            # Télécharger l'avatar
            response = requests.get(avatar_url)
            response.raise_for_status()
            
            # Créer une image à partir des données
            avatar_image = Image.open(io.BytesIO(response.content))
            
            # Redimensionner l'image
            avatar_image = avatar_image.resize((self.avatar_size, self.avatar_size))
            
            # Créer un masque circulaire
            mask = Image.new('L', (self.avatar_size, self.avatar_size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, self.avatar_size, self.avatar_size), fill=255)
            
            # Appliquer le masque
            avatar_image = ImageOps.fit(avatar_image, mask.size, centering=(0.5, 0.5))
            avatar_image.putalpha(mask)
            
            return avatar_image
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'avatar: {e}")
            
            # Créer un avatar par défaut
            default_avatar = Image.new('RGBA', (self.avatar_size, self.avatar_size), COLORS['dark'])
            draw = ImageDraw.Draw(default_avatar)
            draw.ellipse((0, 0, self.avatar_size, self.avatar_size), fill=COLORS['primary'])
            
            # Ajouter les initiales au centre
            try:
                initials = member.name[0].upper()
                font = ImageFont.truetype(os.path.join(FONTS_DIR, 'Montserrat-Bold.ttf'), 64)
                w, h = draw.textbbox((0, 0), initials, font=font)[2:]
                draw.text(((self.avatar_size-w)//2, (self.avatar_size-h)//2-5), 
                         initials, fill=COLORS['light'], font=font)
            except Exception:
                # En cas d'erreur avec les initiales, laissez simplement le cercle
                pass
            
            return default_avatar

    def _create_artistic_background(self, width, height, style, frame_num=0, total_frames=1):
        """
        Crée un fond artistique en fonction du style choisi.
        
        Args:
            width: Largeur de l'image
            height: Hauteur de l'image
            style: Style artistique à appliquer
            frame_num: Numéro de la frame actuelle (pour animations)
            total_frames: Nombre total de frames
            
        Returns:
            Image PIL avec le fond artistique
        """
        # Base image
        background = Image.new('RGBA', (width, height), COLORS['background'])
        draw = ImageDraw.Draw(background)
        
        # Animation progress (0.0 to 1.0)
        progress = frame_num / max(1, total_frames - 1)
        
        if style == 'musical':
            # Créer un motif de lignes ondulées représentant des ondes sonores
            for i in range(0, width, 20):
                amplitude = 30 + 10 * random.random()
                frequency = 0.1 * random.random()
                color = random.choice([COLORS['primary'], COLORS['secondary'], COLORS['accent']])
                
                # Animation : variation des ondes sonores
                phase_shift = progress * 2 * 3.14159  # 0 à 2π
                
                for x in range(0, width, 3):
                    y = int(height/2 + amplitude * 
                            ((frame_num + i) % 5) * 
                            (0.2 + 0.8 * progress) *
                            (0.8 + 0.2 * random.random()) *
                            (0.5 + 0.5 * (x / width)) *
                            (0.8 + 0.2 * random.random()) *
                            (1 + random.random()) *
                            (0.5 + 0.5 * (height / 2 / width)) *
                            (0.9 + 0.1 * (random.random() / x)))
                    if 0 <= y < height:
                        draw.point((x, y), fill=color)
        
        elif style == 'visual':
            # Créer des formes géométriques abstraites
            for _ in range(15):
                shape_type = random.choice(['circle', 'rectangle', 'line'])
                color = random.choice([COLORS['primary'], COLORS['secondary'], 
                                      COLORS['accent'], COLORS['creative']])
                
                # Position avec variation selon l'animation
                x = int(random.random() * width)
                y = int(random.random() * height)
                
                # Taille avec effet de pulsation
                size_factor = 0.7 + 0.6 * abs(progress - 0.5) * 2
                size = int(20 + 60 * random.random() * size_factor)
                
                alpha = int(128 + 127 * random.random())
                color_with_alpha = color[:-1] + (alpha,)
                
                if shape_type == 'circle':
                    draw.ellipse((x, y, x + size, y + size), 
                                fill=color_with_alpha)
                elif shape_type == 'rectangle':
                    rotation = progress * 360
                    rect = Image.new('RGBA', (size, size), color_with_alpha)
                    rect = rect.rotate(rotation, expand=True)
                    background.paste(rect, (x, y), rect)
                elif shape_type == 'line':
                    thickness = int(2 + 5 * random.random())
                    length = int(50 + 100 * random.random())
                    angle = progress * 360
                    end_x = x + int(length * ((frame_num % 3) + 1) * (angle / 180) * 
                                   (0.4 + 0.6 * random.random()))
                    end_y = y + int(length * ((frame_num % 2) + 1) * (angle / 90) * 
                                   (0.4 + 0.6 * random.random()))
                    draw.line((x, y, end_x, end_y), fill=color, width=thickness)
        
        elif style == 'minimal':
            # Ajouter quelques lignes subtiles
            for i in range(0, width, 40):
                color = COLORS['primary'] if i % 80 == 0 else COLORS['secondary']
                alpha = int(30 + 30 * abs(progress - 0.5) * 2)
                color_with_alpha = color[:-1] + (alpha,)
                draw.line((i, 0, i, height), fill=color_with_alpha, width=1)
            
            for i in range(0, height, 40):
                color = COLORS['accent'] if i % 80 == 0 else COLORS['creative']
                alpha = int(20 + 40 * abs(progress - 0.5) * 2)
                color_with_alpha = color[:-1] + (alpha,)
                draw.line((0, i, width, i), fill=color_with_alpha, width=1)
        
        elif style == 'vibrant':
            # Gradients colorés et vibrants
            for x in range(width):
                for y in range(0, height, 3):  # Skip pixels for performance
                    r = int(127 + 127 * ((x + frame_num * 5) % width) / width)
                    g = int(127 + 127 * ((y + frame_num * 3) % height) / height)
                    b = int(127 + 127 * abs(((x + y) / (width + height)) - 0.5) * 2)
                    a = int(10 + 20 * random.random())
                    
                    # Animation : décalage de couleurs
                    r = (r + int(50 * progress)) % 255
                    g = (g + int(30 * (1 - progress))) % 255
                    b = (b + int(40 * abs(progress - 0.5) * 2)) % 255
                    
                    draw.point((x, y), fill=(r, g, b, a))
        
        elif style == 'retro':
            # Style rétro avec grain et couleurs vintage
            retro_colors = [
                (217, 185, 155, 60),  # Sépia clair
                (120, 85, 55, 50),    # Brun vintage
                (158, 130, 106, 40),  # Beige rétro
                (86, 75, 48, 30)      # Olive foncé
            ]
            
            # Ajouter des vignettes (coins assombris)
            vignette = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            vignette_draw = ImageDraw.Draw(vignette)
            
            # Animation : intensité de la vignette
            vignette_intensity = 150 + int(40 * abs(progress - 0.5) * 2)
            
            for i in range(15):
                radius = int(min(width, height) * (0.5 + i * 0.03))
                alpha = max(0, vignette_intensity - i * 10)
                vignette_draw.ellipse(
                    (width//2 - radius, height//2 - radius, 
                     width//2 + radius, height//2 + radius),
                    fill=(0, 0, 0, 0),
                    outline=(0, 0, 0, alpha))
            
            # Ajouter des rayures aléatoires (comme sur de vieux films)
            if random.random() < 0.3:  # Probabilité d'avoir des rayures
                scratch_x = random.randint(0, width - 1)
                scratch_length = random.randint(10, height // 3)
                scratch_y = random.randint(0, height - scratch_length)
                scratch_width = random.randint(1, 3)
                scratch_alpha = random.randint(40, 70)
                vignette_draw.line(
                    (scratch_x, scratch_y, scratch_x, scratch_y + scratch_length),
                    fill=(255, 255, 255, scratch_alpha),
                    width=scratch_width)
            
            # Ajouter un grain rétro
            noise = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            noise_draw = ImageDraw.Draw(noise)
            
            for _ in range(5000):
                x = random.randint(0, width - 1)
                y = random.randint(0, height - 1)
                color = random.choice(retro_colors)
                # Animation : variation du grain
                noise_alpha = int(color[3] * (0.5 + 0.5 * abs(progress - 0.5) * 2))
                noise_color = color[:3] + (noise_alpha,)
                noise_draw.point((x, y), fill=noise_color)
            
            # Combiner les effets
            background = Image.alpha_composite(background, noise)
            background = Image.alpha_composite(background, vignette)
        
        # Appliquer un léger flou pour adoucir l'image
        background = background.filter(ImageFilter.GaussianBlur(radius=1))
        
        return background
    
    def _add_text_elements(self, image, member, frame_num=0, total_frames=1):
        """
        Ajoute les éléments textuels à la carte.
        
        Args:
            image: L'image de fond
            member: Le membre Discord
            frame_num: Numéro de la frame actuelle
            total_frames: Nombre total de frames
            
        Returns:
            Image PIL avec les textes ajoutés
        """
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        # Animation progress (0.0 to 1.0)
        progress = frame_num / max(1, total_frames - 1)
        
        try:
            # Charger les polices
            main_font = ImageFont.truetype(os.path.join(FONTS_DIR, 'Montserrat-Bold.ttf'), 48)
            secondary_font = ImageFont.truetype(os.path.join(FONTS_DIR, 'Poppins-Regular.ttf'), 24)
            accent_font = ImageFont.truetype(os.path.join(FONTS_DIR, 'DancingScript.ttf'), 36)
            
            # Textes
            welcome_text = "Bienvenue"
            name_text = member.display_name
            subtitle_text = "dans Le Séminaire artistique"
            
            # Animer le texte avec une apparition progressive
            text_alpha = int(min(255, 255 * (progress * 2 if progress < 0.5 else 1)))
            
            # Effet de glissement pour le nom
            name_offset_x = int(width * 0.1 * (1 - min(1, progress * 2)))
            
            # Calculer les positions des textes
            welcome_bbox = draw.textbbox((0, 0), welcome_text, font=accent_font)
            welcome_w, welcome_h = welcome_bbox[2] - welcome_bbox[0], welcome_bbox[3] - welcome_bbox[1]
            welcome_x = (width - welcome_w) // 2
            welcome_y = height // 4 - welcome_h // 2
            
            name_bbox = draw.textbbox((0, 0), name_text, font=main_font)
            name_w, name_h = name_bbox[2] - name_bbox[0], name_bbox[3] - name_bbox[1]
            name_x = (width - name_w) // 2 - name_offset_x
            name_y = height // 2 - name_h // 2
            
            subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=secondary_font)
            subtitle_w, subtitle_h = subtitle_bbox[2] - subtitle_bbox[0], subtitle_bbox[3] - subtitle_bbox[1]
            subtitle_x = (width - subtitle_w) // 2
            subtitle_y = height * 3 // 4 - subtitle_h // 2
            
            # Ajouter des ombres pour une meilleure lisibilité
            shadow_offset = 2
            shadow_color = (0, 0, 0, text_alpha // 2)
            
            # Dessiner les textes avec ombre
            # 1. Bienvenue (avec police artistique)
            draw.text((welcome_x + shadow_offset, welcome_y + shadow_offset), 
                     welcome_text, font=accent_font, fill=shadow_color)
            draw.text((welcome_x, welcome_y), 
                     welcome_text, font=accent_font, fill=(255, 215, 0, text_alpha))  # Or
            
            # 2. Nom du membre (en grand et en gras)
            draw.text((name_x + shadow_offset, name_y + shadow_offset), 
                     name_text, font=main_font, fill=shadow_color)
            draw.text((name_x, name_y), 
                     name_text, font=main_font, fill=(255, 255, 255, text_alpha))  # Blanc
            
            # 3. Sous-titre
            draw.text((subtitle_x + shadow_offset, subtitle_y + shadow_offset), 
                     subtitle_text, font=secondary_font, fill=shadow_color)
            draw.text((subtitle_x, subtitle_y), 
                     subtitle_text, font=secondary_font, fill=(114, 137, 218, text_alpha))  # Bleu Discord
            
            return image
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout des textes: {e}")
            return image
    
    def _add_decorative_elements(self, image, style, avatar_image, frame_num=0, total_frames=1):
        """
        Ajoute des éléments décoratifs à la carte.
        
        Args:
            image: L'image de base
            style: Le style artistique
            avatar_image: L'image d'avatar du membre
            frame_num: Numéro de la frame actuelle
            total_frames: Nombre total de frames
            
        Returns:
            Image PIL avec les décorations ajoutées
        """
        width, height = image.size
        
        # Animation progress (0.0 to 1.0)
        progress = frame_num / max(1, total_frames - 1)
        
        # Créer une copie de l'image pour ne pas modifier l'original
        decorated = image.copy()
        
        # Position de l'avatar avec animation
        avatar_factor = min(1, progress * 2)  # 0 à 1 durant la première moitié de l'animation
        avatar_y_offset = int(50 * (1 - avatar_factor))
        avatar_x = (width - self.avatar_size) // 2
        avatar_y = height // 8 - self.avatar_size // 2 - avatar_y_offset
        
        # Animation de l'avatar: apparition progressive
        if avatar_image:
            if progress < 0.5:
                # Premières frames: agrandir l'avatar
                scale_factor = 0.5 + progress
                new_size = int(self.avatar_size * scale_factor)
                resized_avatar = avatar_image.resize((new_size, new_size), Image.LANCZOS)
                
                # Recentrer l'avatar redimensionné
                paste_x = avatar_x - (new_size - self.avatar_size) // 2
                paste_y = avatar_y - (new_size - self.avatar_size) // 2
                
                # Ajuster la transparence
                avatar_alpha = int(255 * (progress * 2))
                
                # Convertir en mode RGBA si nécessaire
                if resized_avatar.mode != 'RGBA':
                    resized_avatar = resized_avatar.convert('RGBA')
                
                # Appliquer la transparence
                r, g, b, a = resized_avatar.split()
                a = a.point(lambda x: min(x, avatar_alpha))
                resized_avatar = Image.merge('RGBA', (r, g, b, a))
                
                # Coller sur l'image
                decorated.paste(resized_avatar, (paste_x, paste_y), resized_avatar)
            else:
                # Frames suivantes: effet de halo ou d'éclat
                glow_intensity = abs((progress - 0.75) * 4)  # 0->1->0 pendant la seconde moitié
                
                # 1. Coller l'avatar original
                decorated.paste(avatar_image, (avatar_x, avatar_y), avatar_image)
                
                # 2. Ajouter un effet de halo/éclat si l'intensité > 0
                if glow_intensity > 0.1:
                    # Créer un halo légèrement plus grand
                    halo_size = int(self.avatar_size * (1 + 0.1 * glow_intensity))
                    halo = Image.new('RGBA', (halo_size, halo_size), (0, 0, 0, 0))
                    halo_draw = ImageDraw.Draw(halo)
                    
                    # Dessiner le halo
                    halo_color = COLORS['highlight']
                    halo_alpha = int(100 * glow_intensity)
                    halo_color_with_alpha = halo_color[:-1] + (halo_alpha,)
                    
                    halo_draw.ellipse((0, 0, halo_size, halo_size), fill=halo_color_with_alpha)
                    
                    # Appliquer un flou pour l'effet de halo
                    halo = halo.filter(ImageFilter.GaussianBlur(radius=int(5 + 5 * glow_intensity)))
                    
                    # Coller le halo derrière l'avatar
                    halo_x = avatar_x - (halo_size - self.avatar_size) // 2
                    halo_y = avatar_y - (halo_size - self.avatar_size) // 2
                    
                    # Créer une image temporaire pour le compositing
                    temp = Image.new('RGBA', decorated.size, (0, 0, 0, 0))
                    temp.paste(halo, (halo_x, halo_y), halo)
                    
                    # Fusionner avec l'image principale
                    decorated = Image.alpha_composite(temp, decorated)
        
        # Ajouter des éléments décoratifs en fonction du style
        if style == 'musical':
            # Ajouter des notes de musique
            notes = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            notes_draw = ImageDraw.Draw(notes)
            
            for i in range(5):
                # Position qui varie avec l'animation
                note_x = int(width * 0.1 + width * 0.8 * random.random() + 
                            width * 0.2 * random.random() * progress)
                note_y = int(height * 0.7 + height * 0.2 * random.random() + 
                            height * 0.1 * random.random() * progress)
                
                # Taille qui peut varier légèrement
                note_size = int(20 + 10 * random.random() + 5 * abs(progress - 0.5) * 2)
                
                # Animation de l'opacité
                opacity = int(200 * min(1, progress * 3 if i % 2 == 0 else (1 - progress) * 3))
                
                # Dessiner une note simple (cercle avec ligne)
                if opacity > 0:
                    note_color = (*ImageColor.getrgb(COLORS['highlight'][:-1]), opacity)
                    notes_draw.ellipse(
                        (note_x, note_y, note_x + note_size//2, note_y + note_size//2),
                        fill=note_color)
                    notes_draw.line(
                        (note_x + note_size//4, note_y + note_size//2, 
                         note_x + note_size//4, note_y - note_size),
                        fill=note_color, width=2)
            
            # Fusionner avec l'image principale
            decorated = Image.alpha_composite(decorated, notes)
            
        elif style == 'visual':
            # Ajouter un cadre artistique
            frame = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            frame_draw = ImageDraw.Draw(frame)
            
            # Largeur du cadre qui varie avec l'animation
            frame_width = int(15 * progress)
            
            if frame_width > 0:
                # Coins arrondis
                corner_radius = 20
                
                # Couleur du cadre avec animation
                hue_shift = int(360 * progress) % 360
                frame_color = self._hue_shift(COLORS['creative'], hue_shift)
                frame_opacity = int(200 * min(1, progress * 2))
                frame_color_with_alpha = frame_color[:-1] + (frame_opacity,)
                
                # Dessiner un rectangle arrondi
                self._rounded_rectangle(
                    frame_draw,
                    (frame_width, frame_width, width - frame_width, height - frame_width),
                    corner_radius, outline=frame_color_with_alpha, width=frame_width)
                
                # Fusionner avec l'image principale
                decorated = Image.alpha_composite(decorated, frame)
        
        elif style == 'retro':
            # Ajouter une bordure style photo vintage
            border_width = int(20 * progress)
            if border_width > 0:
                border = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                border_draw = ImageDraw.Draw(border)
                
                # Couleur sépia pour la bordure
                border_color = (217, 185, 155, int(200 * min(1, progress * 2)))
                
                # Dessiner la bordure
                border_draw.rectangle((0, 0, width, height), outline=border_color, width=border_width)
                
                # Ajouter de petites marques de coins comme sur les photos anciennes
                corner_size = int(40 * progress)
                corner_color = (86, 75, 48, int(220 * min(1, progress * 2)))
                
                # Coin supérieur gauche
                border_draw.line((0, 0, corner_size, 0), fill=corner_color, width=5)
                border_draw.line((0, 0, 0, corner_size), fill=corner_color, width=5)
                
                # Coin supérieur droit
                border_draw.line((width, 0, width - corner_size, 0), fill=corner_color, width=5)
                border_draw.line((width, 0, width, corner_size), fill=corner_color, width=5)
                
                # Coin inférieur gauche
                border_draw.line((0, height, corner_size, height), fill=corner_color, width=5)
                border_draw.line((0, height, 0, height - corner_size), fill=corner_color, width=5)
                
                # Coin inférieur droit
                border_draw.line((width, height, width - corner_size, height), fill=corner_color, width=5)
                border_draw.line((width, height, width, height - corner_size), fill=corner_color, width=5)
                
                # Fusionner avec l'image principale
                decorated = Image.alpha_composite(decorated, border)
        
        return decorated
    
    def _rounded_rectangle(self, draw, rect, radius, outline=None, fill=None, width=1):
        """
        Dessine un rectangle avec des coins arrondis.
        
        Args:
            draw: Object ImageDraw.Draw pour dessiner
            rect: Tuple (x0, y0, x1, y1) définissant le rectangle
            radius: Rayon des coins arrondis
            outline: Couleur de contour
            fill: Couleur de remplissage
            width: Épaisseur du contour
        """
        x0, y0, x1, y1 = rect
        
        # Dessiner les coins
        draw.ellipse((x0, y0, x0 + radius * 2, y0 + radius * 2), 
                    outline=outline, fill=fill, width=width)  # Coin supérieur gauche
        draw.ellipse((x1 - radius * 2, y0, x1, y0 + radius * 2), 
                    outline=outline, fill=fill, width=width)  # Coin supérieur droit
        draw.ellipse((x0, y1 - radius * 2, x0 + radius * 2, y1), 
                    outline=outline, fill=fill, width=width)  # Coin inférieur gauche
        draw.ellipse((x1 - radius * 2, y1 - radius * 2, x1, y1), 
                    outline=outline, fill=fill, width=width)  # Coin inférieur droit
        
        # Dessiner les rectangles pour compléter la forme
        draw.rectangle((x0 + radius, y0, x1 - radius, y1), 
                      outline=outline, fill=fill, width=width)  # Rectangle central horizontal
        draw.rectangle((x0, y0 + radius, x1, y1 - radius), 
                      outline=outline, fill=fill, width=width)  # Rectangle central vertical
    
    def _hue_shift(self, color_hex, degrees):
        """
        Applique un décalage de teinte à une couleur hexadécimale.
        
        Args:
            color_hex: Couleur hexadécimale
            degrees: Degrés de décalage de teinte (0-360)
            
        Returns:
            Couleur hexadécimale modifiée
        """
        # Convertir hex en RGB
        rgb = ImageColor.getrgb(color_hex[:-1])
        
        # Convertir RGB en HSV
        h, s, v = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
        
        # Décaler la teinte
        h = ((h * 360 + degrees) % 360) / 360
        
        # Convertir HSV en RGB
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        r, g, b = int(r * 255), int(g * 255), int(b * 255)
        
        # Retourner le format hexadécimal
        return f'#{r:02x}{g:02x}{b:02x}FF'
    
    async def generate_welcome_card(self, member, style=None, animation=None):
        """
        Génère une carte de bienvenue animée pour un nouveau membre.
        
        Args:
            member: Le membre Discord
            style: Style artistique à utiliser (si None, un style est choisi aléatoirement)
            animation: Type d'animation à utiliser (si None, une animation est choisie aléatoirement)
            
        Returns:
            Chemin du fichier GIF animé généré
        """
        # Choisir un style et une animation aléatoires si non spécifiés
        if style is None:
            style = random.choice(STYLES)
        if animation is None:
            animation = random.choice(ANIMATIONS)
        
        logger.info(f"Génération d'une carte de bienvenue pour {member.name} (Style: {style}, Animation: {animation})")
        
        try:
            # Récupérer l'avatar du membre
            avatar_image = await self._get_avatar_image(member)
            
            # Créer les frames de l'animation
            frames = []
            for i in range(self.frame_count):
                # Créer le fond artistique
                background = self._create_artistic_background(
                    self.default_width, self.default_height, style, i, self.frame_count)
                
                # Ajouter les éléments textuels
                background = self._add_text_elements(background, member, i, self.frame_count)
                
                # Ajouter les éléments décoratifs et l'avatar
                background = self._add_decorative_elements(
                    background, style, avatar_image, i, self.frame_count)
                
                # Convertir en RGB pour imageio
                if background.mode == 'RGBA':
                    background_rgb = Image.new("RGB", background.size, (0, 0, 0))
                    background_rgb.paste(background, mask=background.split()[3])
                else:
                    background_rgb = background.convert('RGB')
                
                frames.append(background_rgb)
            
            # Créer un fichier GIF temporaire
            with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_file:
                gif_path = temp_file.name
            
            # Enregistrer le GIF
            imageio.mimsave(gif_path, frames, duration=0.1, loop=0)
            
            logger.info(f"Carte de bienvenue générée avec succès: {gif_path}")
            return gif_path
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la carte de bienvenue: {e}")
            return None
    
    async def send_welcome_card(self, member, channel, style=None, animation=None, personal_message=None):
        """
        Génère et envoie une carte de bienvenue animée dans un canal Discord.
        
        Args:
            member: Le membre Discord
            channel: Le canal où envoyer la carte
            style: Style artistique à utiliser
            animation: Type d'animation à utiliser
            personal_message: Message personnalisé à ajouter (si None, utilise un message par défaut)
            
        Returns:
            bool: True si l'envoi a réussi, False sinon
        """
        try:
            # Déterminer le style à utiliser en fonction du profil du membre
            if style is None:
                # Si le membre a un certain rôle, suggérer un style associé
                member_roles = [role.name.lower() for role in member.roles]
                
                if 'musicien' in member_roles or 'rappeur' in member_roles or 'beatmaker' in member_roles:
                    style = 'musical'
                elif 'graphiste' in member_roles or 'photographe' in member_roles or 'vidéaste' in member_roles:
                    style = 'visual'
                elif 'admin' in member_roles or 'modérateur' in member_roles:
                    style = 'vibrant'
                else:
                    # Sinon, choisir aléatoirement
                    style = random.choice(STYLES)
            
            # Générer la carte de bienvenue
            card_path = await self.generate_welcome_card(member, style, animation)
            
            if card_path:
                # Déterminer le message de bienvenue approprié
                if personal_message is None:
                    messages = [
                        f"🎨 **Bienvenue {member.mention} dans Le Séminaire !** 🎤",
                        f"🎉 **Un nouvel artiste rejoint Le Séminaire !** Bienvenue {member.mention} !",
                        f"✨ **Bienvenue dans notre communauté créative, {member.mention} !**",
                        f"🌟 **{member.mention} vient d'arriver !** Accueillons chaleureusement ce nouvel artiste !",
                        f"🔥 **Nouvel artiste détecté !** Bienvenue {member.mention} dans Le Séminaire !",
                    ]
                    welcome_line = random.choice(messages)
                    
                    second_lines = [
                        "N'hésite pas à te présenter dans <#présentation-artistes> et à explorer les différents canaux !",
                        "Nous sommes ravis de te compter parmi nous ! Présente-toi et découvre notre communauté.",
                        "Parle-nous de ton art, de tes influences et de tes projets !",
                        "Quelle est ta discipline artistique ? N'hésite pas à partager ton univers avec nous !",
                        "Découvre nos résidences artistiques et nos événements à venir !"
                    ]
                    welcome_message = f"{welcome_line}\n{random.choice(second_lines)}"
                else:
                    welcome_message = personal_message
                
                # Envoyer la carte avec le message
                with open(card_path, 'rb') as f:
                    await channel.send(welcome_message, file=discord.File(f, filename='welcome.gif'))
                
                # Supprimer le fichier temporaire
                os.unlink(card_path)
                
                logger.info(f"Carte de bienvenue personnalisée envoyée pour {member.name} (style: {style})")
                return True
            else:
                # En cas d'échec, envoyer un message de bienvenue simple
                welcome_message = f"🎨 **Bienvenue {member.mention} dans Le Séminaire !** 🎤\n"
                welcome_message += "N'hésite pas à te présenter dans <#présentation-artistes> et à explorer les différents canaux !"
                
                await channel.send(welcome_message)
                logger.warning(f"Utilisation du message de bienvenue simple pour {member.name} (échec de la génération de carte)")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la carte de bienvenue: {e}")
            return False

# Initialiser les outils nécessaires
try:
    import colorsys
except ImportError:
    # Le module colorsys est nécessaire pour les changements de couleur
    logger.error("Module colorsys manquant, certaines fonctionnalités sont désactivées")

# Classe de base pour les modèles de cartes de bienvenue
class WelcomeCardTemplate:
    """Classe de base pour les différents modèles de cartes de bienvenue"""
    
    @staticmethod
    def get_template_list():
        """Renvoie la liste des modèles disponibles"""
        return [
            "default",
            "musical",
            "artistic",
            "minimal",
            "vintage",
            "modern"
        ]
    
    @staticmethod
    def get_template_description(template_name):
        """Renvoie la description d'un modèle"""
        descriptions = {
            "default": "Modèle standard avec avatar et texte de bienvenue",
            "musical": "Thème musical avec notes et ondes sonores",
            "artistic": "Design créatif avec éléments graphiques et couleurs vives",
            "minimal": "Style épuré et minimaliste",
            "vintage": "Esthétique rétro avec effets anciens",
            "modern": "Design contemporain avec formes géométriques"
        }
        return descriptions.get(template_name, "Description non disponible")