"""
RetroFormat Browser-Style Profile Manager
Implements isolated user profiles where each profile is an independent workspace
and new profiles start completely from scratch (like Google Chrome / Brave / Edge profiles).
"""

import os
import sys
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from data.packages import PACKAGES
from data.tweaks import TWEAKS
from backup_manager import BACKUP_ITEMS

VALID_APP_IDS = {p["id"] for p in PACKAGES}
VALID_TWEAK_IDS = {t["id"] for t in TWEAKS}
VALID_BACKUP_IDS = {b["id"] for b in BACKUP_ITEMS}

APP_MAP = {p["id"]: p for p in PACKAGES}
TWEAK_MAP = {t["id"]: t for t in TWEAKS}
BACKUP_MAP = {b["id"]: b for b in BACKUP_ITEMS}


class BrowserProfileManager:
    """Manages browser-like isolated user profiles for RetroFormat.
    
    Each profile contains its own independent selections for apps, tweaks,
    backups, and backup directory. New profiles start completely clean (from scratch).
    """

    def __init__(self):
        self.storage_path = self._get_storage_path()
        self.active_profile_id: str = "prof_default"
        self.profiles: List[Dict[str, Any]] = []
        self.load()

    def _get_storage_path(self) -> str:
        """Determines persistent storage path for profiles.
        Never writes to temporary PyInstaller extraction directories.
        """
        # Check portable profiles.json alongside executable
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        portable_file = os.path.join(base_dir, "profiles.json")
        if os.path.isfile(portable_file):
            return portable_file

        app_data = os.environ.get("APPDATA")
        if not app_data:
            app_data = os.path.expanduser("~")
        retro_dir = os.path.join(app_data, "RetroFormat")
        try:
            os.makedirs(retro_dir, exist_ok=True)
        except Exception:
            pass
        return os.path.join(retro_dir, "profiles.json")

    def load(self):
        """Loads profiles from JSON storage or initializes default clean profile."""
        self.profiles = []
        self.theme = "dark"
        if os.path.isfile(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.active_profile_id = data.get("active_profile_id", "prof_default")
                    self.theme = data.get("theme", "dark")
                    raw_profs = data.get("profiles", [])
                    if isinstance(raw_profs, list):
                        for p in raw_profs:
                            sanitized = self._sanitize_profile(p)
                            if sanitized:
                                self.profiles.append(sanitized)
            except Exception as e:
                print(f"[ProfileManager] Profil yüklenirken hata: {e}")

        # If no profiles found, create initial default profile starting from scratch
        if not self.profiles:
            default_prof = {
                "id": "prof_default",
                "name": "Varsayılan Profil",
                "icon": "👤",
                "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "apps": [],
                "tweaks": [],
                "backups": [],
                "backup_dir": ""
            }
            self.profiles.append(default_prof)
            self.active_profile_id = "prof_default"
            self.save()
        else:
            # Ensure active_profile_id is valid
            valid_ids = [p["id"] for p in self.profiles]
            if self.active_profile_id not in valid_ids:
                self.active_profile_id = valid_ids[0]

    def get_theme(self) -> str:
        return getattr(self, "theme", "dark")

    def set_theme(self, theme: str) -> bool:
        self.theme = "light" if theme == "light" else "dark"
        return self.save()

    def save(self) -> bool:
        """Saves all profiles and active profile pointer to persistent JSON storage."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            data = {
                "version": "3.0",
                "type": "retroformat_browser_profiles",
                "active_profile_id": self.active_profile_id,
                "theme": getattr(self, "theme", "dark"),
                "profiles": self.profiles
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ProfileManager] Profil kaydedilirken hata: {e}")
            return False

    def _sanitize_profile(self, raw: Any) -> Optional[Dict[str, Any]]:
        """Cleans and validates a profile object, ensuring all keys exist."""
        if not isinstance(raw, dict):
            return None

        prof_id = str(raw.get("id", f"prof_{uuid.uuid4().hex[:6]}"))
        name = str(raw.get("name", "Profil")).strip() or "İsimsiz Profil"
        icon = str(raw.get("icon", "👤")).strip() or "👤"
        created_at = str(raw.get("created_at", datetime.now().strftime("%d.%m.%Y %H:%M")))

        raw_apps = raw.get("apps", [])
        apps = [str(x) for x in raw_apps if str(x) in VALID_APP_IDS] if isinstance(raw_apps, list) else []

        raw_tweaks = raw.get("tweaks", [])
        tweaks = [str(x) for x in raw_tweaks if str(x) in VALID_TWEAK_IDS] if isinstance(raw_tweaks, list) else []

        raw_backups = raw.get("backups", [])
        backups = [str(x) for x in raw_backups if str(x) in VALID_BACKUP_IDS] if isinstance(raw_backups, list) else []

        backup_dir = str(raw.get("backup_dir", "")).strip()

        return {
            "id": prof_id,
            "name": name,
            "icon": icon,
            "created_at": created_at,
            "apps": apps,
            "tweaks": tweaks,
            "backups": backups,
            "backup_dir": backup_dir
        }

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        """Returns list of all available profiles."""
        return self.profiles

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Gets a profile by its unique ID."""
        for p in self.profiles:
            if p["id"] == profile_id:
                return p
        return None

    def get_active_profile(self) -> Dict[str, Any]:
        """Returns the currently active profile."""
        prof = self.get_profile(self.active_profile_id)
        if not prof:
            if self.profiles:
                self.active_profile_id = self.profiles[0]["id"]
                return self.profiles[0]
            # Fallback fresh profile
            return {
                "id": "prof_default",
                "name": "Varsayılan Profil",
                "icon": "👤",
                "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "apps": [],
                "tweaks": [],
                "backups": [],
                "backup_dir": ""
            }
        return prof

    def set_active_profile_id(self, profile_id: str) -> bool:
        """Switches active profile to the given ID."""
        if self.get_profile(profile_id):
            self.active_profile_id = profile_id
            self.save()
            return True
        return False

    def create_new_profile(self, name: str, icon: str = "👤") -> Dict[str, Any]:
        """Creates a brand new profile that starts completely from scratch (clean / empty).
        Sets the new profile as active immediately.
        """
        prof_id = f"prof_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
        clean_name = name.strip() or f"Profil {len(self.profiles) + 1}"
        new_prof = {
            "id": prof_id,
            "name": clean_name,
            "icon": icon or "👤",
            "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "apps": [],       # Starts completely from scratch
            "tweaks": [],     # Starts completely from scratch
            "backups": [],    # Starts completely from scratch
            "backup_dir": ""
        }
        self.profiles.append(new_prof)
        self.active_profile_id = prof_id
        self.save()
        return new_prof

    def update_active_selections(
        self,
        apps: Optional[List[str]] = None,
        tweaks: Optional[List[str]] = None,
        backups: Optional[List[str]] = None,
        backup_dir: Optional[str] = None
    ) -> bool:
        """Live auto-saves current checkbox selections to the active profile."""
        active = self.get_active_profile()
        modified = False
        if apps is not None:
            active["apps"] = [a for a in apps if a in VALID_APP_IDS]
            modified = True
        if tweaks is not None:
            active["tweaks"] = [t for t in tweaks if t in VALID_TWEAK_IDS]
            modified = True
        if backups is not None:
            active["backups"] = [b for b in backups if b in VALID_BACKUP_IDS]
            modified = True
        if backup_dir is not None:
            active["backup_dir"] = backup_dir.strip()
            modified = True

        if modified:
            return self.save()
        return False

    def rename_profile(self, profile_id: str, new_name: str, new_icon: Optional[str] = None) -> bool:
        """Renames a profile and optionally changes its icon."""
        prof = self.get_profile(profile_id)
        if prof:
            prof["name"] = new_name.strip()
            if new_icon:
                prof["icon"] = new_icon.strip()
            return self.save()
        return False

    def clear_profile_selections(self, profile_id: str) -> bool:
        """Clears all selections for a profile, returning it to a scratch state."""
        prof = self.get_profile(profile_id)
        if prof:
            prof["apps"] = []
            prof["tweaks"] = []
            prof["backups"] = []
            return self.save()
        return False

    def delete_profile(self, profile_id: str) -> bool:
        """Deletes a profile. Cannot delete if it is the only profile left."""
        if len(self.profiles) <= 1:
            return False  # Must keep at least one profile

        for idx, prof in enumerate(self.profiles):
            if prof["id"] == profile_id:
                self.profiles.pop(idx)
                if self.active_profile_id == profile_id:
                    self.active_profile_id = self.profiles[0]["id"]
                self.save()
                return True
        return False

    def export_profile_to_file(self, profile_id: str, file_path: str) -> bool:
        """Exports an isolated profile to a standalone JSON file for USB transport."""
        prof = self.get_profile(profile_id)
        if not prof:
            return False

        export_data = {
            "version": "3.0",
            "type": "retroformat_browser_profile",
            "exported_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "profile": prof
        }
        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ProfileManager] Dışa aktarma hatası: {e}")
            return False

    def import_profile_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Imports a profile from a JSON file, adds it to the profile list,
        and sets it as the active profile.
        """
        if not os.path.isfile(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            if not isinstance(raw_data, dict):
                return None

            prof_data = raw_data.get("profile", raw_data)
            sanitized = self._sanitize_profile(prof_data)
            if not sanitized:
                return None

            # Generate fresh unique ID to avoid collision
            sanitized["id"] = f"prof_imp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            if not sanitized.get("name") or sanitized["name"] == "İsimsiz Profil":
                sanitized["name"] = f"İçe Aktarılan ({base_name})"

            self.profiles.append(sanitized)
            self.active_profile_id = sanitized["id"]
            self.save()
            return sanitized
        except Exception as e:
            print(f"[ProfileManager] İçe aktarma hatası: {e}")
            return None
