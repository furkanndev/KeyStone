from .browsers import Browsers
from .devenv import GitSsh, Shell
from .editors import Editors
from .more import (Downloads, GameSaves, HostsFile, JetBrains, Obs, RemoteTools, StartupApps,
                   UserFolders, Wallpaper, WindowsApps, WindowsSettings)
from .system import ActiveTweaks, Apps, Desktop, EnvVars, Fonts
from .wifi import Wifi

ITEMS = [Apps(), Browsers(), Wifi(), Editors(), JetBrains(), GitSsh(), RemoteTools(), Shell(), EnvVars(),
         WindowsSettings(), WindowsApps(), Wallpaper(), StartupApps(), Desktop(), Fonts(), GameSaves(), Obs(),
         HostsFile(), ActiveTweaks(), UserFolders(), Downloads()]
BY_ID = {i.id: i for i in ITEMS}
