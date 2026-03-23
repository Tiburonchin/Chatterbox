#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chatterbox TTS Service
Orquestador para synthesis de voz con Chatterbox
Sin dependencias externas complejas - Solo lo necesario

Path: scripts/tts_server/chatterbox_service.py
"""

import torch
import torchaudio as ta
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class ChatterboxTTSService:
    """
    Servicio TTS con Chatterbox
    
    Soporta:
    - Chatterbox-Turbo (350M, baja latencia, Inglés)
    - Chatterbox-Multilingual (500M, 23+ idiomas)
    - Voice cloning (zero-shot)
    - Sin cURL - Python puro
    """
    
    SUPPORTED_LANGUAGES = [
        'ar', 'da', 'de', 'el', 'en', 'es', 'fi', 'fr', 'he', 'hi',
        'it', 'ja', 'ko', 'ms', 'nl', 'no', 'pl', 'pt', 'ru', 'sv',
        'sw', 'tr', 'zh'
    ]
    
    def __init__(self, model: str = 'turbo', device: str = 'cpu'):
        """
        Inicializar servicio
        
        Args:
            model: 'turbo', 'multilingual', 'classic'
            device: 'cuda', 'cpu', 'mps'
        """
        self.model_type = model
        self.device = device
        self.model = None
        self.sr = 44100  # Sample rate
        
        self._load_model()
    
    def _load_model(self):
        """Cargar modelo de Chatterbox"""
        try:
            if self.model_type == 'turbo':
                from chatterbox.tts_turbo import ChatterboxTurboTTS
                self.model = ChatterboxTurboTTS.from_pretrained(device=self.device)
            elif self.model_type == 'multilingual':
                from chatterbox.mtl_tts import ChatterboxMultilingualTTS
                self.model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
            else:  # classic
                from chatterbox.tts import ChatterboxTTS
                self.model = ChatterboxTTS.from_pretrained(device=self.device)
            
            self.sr = self.model.sr if hasattr(self.model, 'sr') else 44100
        
        except ImportError:
            raise RuntimeError(
                "Chatterbox no está instalado. "
                "Ejecuta: pip install chatterbox-tts torch torchaudio"
            )
        except Exception as e:
            raise RuntimeError(f"Error cargando modelo Chatterbox: {str(e)}")
    
    def synthesize(
        self,
        text: str,
        language_id: str = 'en',
        reference_audio: Optional[str] = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Generar audio de texto
        
        Args:
            text: Texto a convertir (max 5000 chars)
            language_id: Código de idioma ('en', 'es', 'fr', etc.)
            reference_audio: Ruta a WAV para voice cloning
            exaggeration: Control expresividad (0-1)
            cfg_weight: Control CFG (0-1)
        
        Returns:
            {
                'success': bool,
                'file_path': str (si success),
                'duration': float,
                'hash': str,
                'model': str,
                'language': str,
                'error': str (si error)
            }
        """
        try:
            # Validaciones
            text = text.strip() if isinstance(text, str) else ''
            if not text:
                return {'success': False, 'error': 'Texto vacío'}
            if len(text) > 5000:
                return {'success': False, 'error': 'Texto muy largo (max 5000 caracteres)'}
            
            # Validar idioma
            if self.model_type != 'turbo' and language_id not in self.SUPPORTED_LANGUAGES:
                return {
                    'success': False,
                    'error': f'Idioma no soportado: {language_id}'
                }
            
            # Validar archivo de referencia
            if reference_audio and not Path(reference_audio).exists():
                return {
                    'success': False,
                    'error': f'Audio de referencia no existe: {reference_audio}'
                }
            
            # ========== GENERAR AUDIO ==========
            
            if self.model_type == 'turbo':
                # Chatterbox-Turbo (Inglés solamente)
                if reference_audio:
                    wav = self.model.generate(text, audio_prompt_path=reference_audio)
                else:
                    wav = self.model.generate(text)
            
            else:
                # Chatterbox Multilingual o Classic
                if reference_audio:
                    wav = self.model.generate(
                        text,
                        language_id=language_id,
                        audio_prompt_path=reference_audio,
                        exaggeration=exaggeration,
                        cfg_weight=cfg_weight
                    )
                else:
                    wav = self.model.generate(
                        text,
                        language_id=language_id,
                        exaggeration=exaggeration,
                        cfg_weight=cfg_weight
                    )
            
            # Guardar archivo
            output_path = self._save_audio(wav)
            
            # Calcular metadata
            duration = len(wav) / self.sr
            text_hash = hashlib.sha256(
                f"{text}_{language_id}_{self.model_type}".encode()
            ).hexdigest()[:16]
            
            return {
                'success': True,
                'file_path': str(output_path),
                'duration': round(duration, 2),
                'hash': text_hash,
                'model': self.model_type,
                'language': language_id,
                'sample_rate': self.sr,
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'{self.__class__.__name__} error: {str(e)}'
            }
    
    def _save_audio(self, wav: torch.Tensor) -> Path:
        """
        Guardar WAV a archivo
        
        Args:
            wav: Tensor de audio PyTorch
        
        Returns:
            Path al archivo guardado
        """
        output_dir = Path(__file__).parent.parent / 'audio_output'
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Nombre único con timestamp
        timestamp = int(datetime.now().timestamp() * 1000)
        filename = f'tts_{timestamp}.wav'
        output_path = output_dir / filename
        
        # Asegurar que el tensor está en CPU y es float32
        if wav.device.type != 'cpu':
            wav = wav.cpu()
        
        wav = wav.float()
        
        # Guardar
        ta.save(str(output_path), wav, self.sr)
        
        return output_path
    
    def get_info(self) -> Dict[str, Any]:
        """Obtener información del servicio"""
        return {
            'model': self.model_type,
            'device': self.device,
            'sample_rate': self.sr,
            'supported_languages': self.SUPPORTED_LANGUAGES if self.model_type != 'turbo' else ['en'],
            'max_text_length': 5000,
        }


def main():
    """Función principal para testing (ejecutar directo)"""
    import sys
    
    # Test 1: Cargar servicio
    print("✓ Cargando Chatterbox...")
    service = ChatterboxTTSService(model='turbo', device='cpu')
    print(f"  Modelo: {service.model_type}")
    print(f"  Dispositivo: {service.device}")
    
    # Test 2: Generar audio simple
    print("\n✓ Generando audio de prueba...")
    result = service.synthesize("Hello world, this is a test.")
    print(json.dumps(result, indent=2))
    
    # Test 3: Verificar archivo
    if result['success']:
        path = Path(result['file_path'])
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"\n✓ Archivo guardado: {path.name} ({size_mb:.2f} MB)")
        else:
            print(f"\n✗ Archivo no encontrado: {path}")
    else:
        print(f"\n✗ Error: {result['error']}")
        sys.exit(1)


if __name__ == '__main__':
    main()
