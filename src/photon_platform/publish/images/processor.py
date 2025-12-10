from PIL import Image, ImageOps
import hashlib
import os
import shutil
from pathlib import Path

class ImageProcessor:
    """
    Handles image processing including resizing, format conversion (WebP),
    and caching.
    """
    
    def __init__(self, app):
        self.app = app
        self.srcdir = Path(app.srcdir)
        self.outdir = Path(app.outdir)
        
        # Internal cache directory (persistent across builds if config allows)
        self.cache_dir = Path(app.doctreedir).parent / 'photon_cache'
        self.final_images_dir = self.outdir / '_images'
        
        self.ensure_dirs()

    def ensure_dirs(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.final_images_dir.mkdir(parents=True, exist_ok=True)

    def get_image_hash(self, source_path, width, options):
        """
        Generate a unique hash based on file content and processing options.
        """
        hasher = hashlib.sha256()
        
        # Hash file content
        with open(source_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
                
        # Hash parameters
        params = f"{width}-{options}".encode('utf-8')
        hasher.update(params)
        
        return hasher.hexdigest()

    def process_image(self, rel_source_path, options=None):
        """
        Main entry point to process an image.
        
        Returns:
            dict: Paths to the processed 'main' and 'thumb' images relative to output root.
        """
        options = options or {}
        
        abs_source_path = (self.srcdir / rel_source_path).resolve()
        
        if not abs_source_path.exists():
            raise FileNotFoundError(f"Image not found: {abs_source_path}")

        # Specs
        specs = {
            'main': {'width': 800, 'lossless': True, 'quality': None},
            'thumb': {'width': 300, 'lossless': False, 'quality': 80}
        }
        
        results = {}
        original_stem = abs_source_path.stem

        # Calculate relative path of the source directory from srcdir
        rel_dir = abs_source_path.parent.relative_to(self.srcdir)
        
        for variant, spec in specs.items():
            img_hash = self.get_image_hash(abs_source_path, spec['width'], str(spec))
            short_hash = img_hash[:8]
            filename = f"{original_stem}_{spec['width']}w_{short_hash}.webp"
            
            # Cache location remains flat or structured? Flat is easier for cache management, 
            # but structured output is requested. Let's keep cache flat for simplicity/uniqueness 
            # (since hash is unique) OR structure it too. Flat cache is fine.
            cached_path = self.cache_dir / filename
            
            # Final path mirrors source structure
            dest_dir = self.outdir / rel_dir
            dest_dir.mkdir(parents=True, exist_ok=True)
            final_path = dest_dir / filename
            
            # Check cache
            if not cached_path.exists():
                self._generate_variant(abs_source_path, cached_path, spec)
            
            # Copy to build output
            if not final_path.exists() or final_path.stat().st_mtime < cached_path.stat().st_mtime:
                shutil.copy2(cached_path, final_path)
            
            # Return path relative to output root (e.g. usage/figures/img.webp)
            # This is what 'pathto' expects for resource=1
            results[variant] = (rel_dir / filename).as_posix()
            
        # Also copy the original file to the destination
        original_dest_path = self.outdir / rel_dir / abs_source_path.name
        if not original_dest_path.exists() or original_dest_path.stat().st_mtime < abs_source_path.stat().st_mtime:
            shutil.copy2(abs_source_path, original_dest_path)
        
        results['original'] = (rel_dir / abs_source_path.name).as_posix()
            
        return results

    def _generate_variant(self, source_path, output_path, spec):
        """
        Actual Pillow processing logic.
        """
        with Image.open(source_path) as img:
            # Handle RGBA for WebP. If preserving transparency, RGBA is fine.
            # Convert palette mode to RGBA/RGB
            if img.mode == 'P':
                img = img.convert('RGBA')

            width = spec['width']
            
            # Create a copy to resize
            # Use Image.thumbnail to preserve aspect ratio (never crops)
            # For thumbnails, specs said "max-width: 300px", so thumbnail is appropriate.
            # If we wanted exact squares, we'd use ImageOps.fit
            
            processed = img.copy()
            processed.thumbnail((width, width), Image.Resampling.LANCZOS)
            
            save_kwargs = {'format': 'WEBP'}
            if spec['lossless']:
                save_kwargs['lossless'] = True
            else:
                save_kwargs['quality'] = spec['quality']
                
            processed.save(output_path, **save_kwargs)
