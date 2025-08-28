"""
LRU Voice Cache - Manages cached audio files with automatic cleanup.
Provides high-speed access to previously generated TTS audio.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from collections import OrderedDict
import logging

logger = logging.getLogger("alice.voice.cache")

class VoiceCache:
    """
    LRU cache for voice audio files with disk storage.
    Automatically manages cache size and cleans up old files.
    """
    
    def __init__(self, max_size: int = 300):
        self.max_size = max_size
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Stats tracking
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0
        }
        
        # Cache metadata file
        self.cache_dir = Path(__file__).parent / "audio"
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "cache_index.json"
        
        # Load existing cache on startup
        self._load_cache_index()
        
        logger.info(f"VoiceCache initialized: max_size={max_size}, current_size={len(self.cache)}")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached audio data by key (LRU access)"""
        
        self.stats["total_requests"] += 1
        
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            
            # Verify file still exists
            cached_data = self.cache[key]
            audio_file = cached_data.get("audio_file")
            
            if audio_file and Path(audio_file).exists():
                self.stats["hits"] += 1
                logger.debug(f"Cache hit: {key[:16]}...")
                return cached_data
            else:
                # File was deleted - remove from cache
                logger.warning(f"Cache entry invalid (file missing): {key[:16]}...")
                del self.cache[key]
                self._save_cache_index()
        
        self.stats["misses"] += 1
        logger.debug(f"Cache miss: {key[:16]}...")
        return None
    
    def put(self, key: str, data: Dict[str, Any]) -> None:
        """Store audio data in cache with LRU eviction"""
        
        # If key already exists, update it
        if key in self.cache:
            self.cache[key] = data
            self.cache.move_to_end(key)
            self._save_cache_index()
            return
        
        # If cache is full, evict oldest entry
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        # Add new entry
        self.cache[key] = data
        logger.debug(f"Cache put: {key[:16]}... -> {Path(data.get('audio_file', '')).name}")
        
        self._save_cache_index()
    
    def _evict_oldest(self) -> None:
        """Remove the least recently used cache entry"""
        
        if not self.cache:
            return
            
        # Remove oldest (first) entry
        oldest_key, oldest_data = self.cache.popitem(last=False)
        
        # Delete associated audio file if it exists
        audio_file = oldest_data.get("audio_file")
        if audio_file:
            try:
                Path(audio_file).unlink(missing_ok=True)
                logger.debug(f"Evicted audio file: {Path(audio_file).name}")
            except Exception as e:
                logger.warning(f"Failed to delete evicted audio file: {e}")
        
        self.stats["evictions"] += 1
        logger.debug(f"Cache eviction: {oldest_key[:16]}...")
    
    def _load_cache_index(self) -> None:
        """Load cache index from disk on startup"""
        
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Validate and load entries
            valid_entries = 0
            for key, data in cache_data.items():
                audio_file = data.get("audio_file")
                if audio_file and Path(audio_file).exists():
                    self.cache[key] = data
                    valid_entries += 1
                else:
                    # Skip entries with missing files
                    logger.debug(f"Skipping cache entry with missing file: {key[:16]}...")
            
            logger.info(f"Loaded cache index: {valid_entries}/{len(cache_data)} entries valid")
            
        except Exception as e:
            logger.error(f"Failed to load cache index: {e}")
            self.cache.clear()
    
    def _save_cache_index(self) -> None:
        """Save current cache index to disk"""
        
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(dict(self.cache), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")
    
    def cleanup_orphaned_files(self) -> int:
        """Remove audio files not referenced in cache"""
        
        # Get all audio files in directory
        audio_files = set()
        for pattern in ["*.mp3", "*.wav", "*.ogg"]:
            audio_files.update(self.cache_dir.glob(pattern))
        
        # Get files referenced in cache
        cached_files = set()
        for data in self.cache.values():
            audio_file = data.get("audio_file")
            if audio_file:
                cached_files.add(Path(audio_file))
        
        # Remove orphaned files
        orphaned = audio_files - cached_files - {self.cache_file}  # Exclude cache index
        cleaned_count = 0
        
        for orphaned_file in orphaned:
            try:
                orphaned_file.unlink()
                cleaned_count += 1
                logger.debug(f"Cleaned orphaned file: {orphaned_file.name}")
            except Exception as e:
                logger.warning(f"Failed to clean orphaned file {orphaned_file}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned {cleaned_count} orphaned audio files")
        
        return cleaned_count
    
    def clear(self) -> int:
        """Clear entire cache and delete all audio files"""
        
        deleted_count = 0
        
        # Delete all cached audio files
        for data in self.cache.values():
            audio_file = data.get("audio_file")
            if audio_file:
                try:
                    Path(audio_file).unlink(missing_ok=True)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete audio file during clear: {e}")
        
        # Clear cache and stats
        self.cache.clear()
        self.stats = {
            "hits": 0,
            "misses": 0, 
            "evictions": 0,
            "total_requests": 0
        }
        
        # Remove cache index file
        try:
            self.cache_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to delete cache index: {e}")
        
        logger.info(f"Cache cleared: {deleted_count} files deleted")
        return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        
        total_requests = self.stats["total_requests"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "utilization": len(self.cache) / self.max_size * 100,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 1),
            "cache_dir": str(self.cache_dir)
        }
    
    def get_oldest_entries(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get oldest cache entries for debugging"""
        
        entries = []
        for i, (key, data) in enumerate(self.cache.items()):
            if i >= count:
                break
            
            audio_file = data.get("audio_file", "")
            entries.append({
                "key": key[:16] + "...",
                "file": Path(audio_file).name if audio_file else "None",
                "created_at": data.get("created_at", 0),
                "duration": data.get("duration", 0)
            })
        
        return entries
    
    def get_recent_entries(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get most recent cache entries for debugging"""
        
        entries = []
        items = list(self.cache.items())
        
        for i in range(min(count, len(items))):
            key, data = items[-(i+1)]  # Start from the end
            
            audio_file = data.get("audio_file", "")
            entries.append({
                "key": key[:16] + "...",
                "file": Path(audio_file).name if audio_file else "None", 
                "created_at": data.get("created_at", 0),
                "duration": data.get("duration", 0)
            })
        
        return entries