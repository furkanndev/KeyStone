from .browsers import Browsers
from .devenv import GitSsh, Shell
from .editors import Editors
from .system import ActiveTweaks, Apps, Desktop, EnvVars, Fonts
from .wifi import Wifi

ITEMS = [Apps(), Browsers(), Wifi(), Editors(), GitSsh(), Shell(), EnvVars(), Desktop(), Fonts(), ActiveTweaks()]
BY_ID = {i.id: i for i in ITEMS}
