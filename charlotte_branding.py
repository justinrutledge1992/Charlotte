"""
Charlotte Web Archiver - ASCII Art and Branding
"""

CHARLOTTE_ASCII = r"""
    _____ _                _       _   _       
   / ____| |              | |     | | | |      
  | |    | |__   __ _ _ __| | ___ | |_| |_ ___ 
  | |    | '_ \ / _` | '__| |/ _ \| __| __/ _ \
  | |____| | | | (_| | |  | | (_) | |_| ||  __/
   \_____|_| |_|\__,_|_|  |_|\___/ \__|\__\___|
                                                
        Web Archiver - "Some Spider!"
        
  Named after Charlotte from Charlotte's Web
"""

CHARLOTTE_SMALL = r"""
  Charlotte 🕷️  - Web Archiver
  "Some Spider!"
"""

WEB_PATTERN = r"""
        ╱╲      ╱╲
       ╱  ╲    ╱  ╲
      ╱____╲__╱____╲
      ╲    ╱  ╲    ╱
       ╲  ╱    ╲  ╱
        ╲╱      ╲╱
"""

SPIDER_SMALL = "🕷️"

QUOTES = [
    '"Salutations!" - Charlotte',
    '"Some spider!" - Charlotte\'s Web',
    '"Charlotte was both a true friend and a good writer."',
    '"I am working on my web. I make a web to catch flies."',
    '"But I am going to save you, and I want you to quiet down immediately."',
]


def print_banner():
    """Print the Charlotte ASCII art banner"""
    print(CHARLOTTE_ASCII)


def print_small_banner():
    """Print a small Charlotte banner"""
    print(CHARLOTTE_SMALL)


def get_random_quote():
    """Get a random Charlotte quote"""
    import random
    return random.choice(QUOTES)


if __name__ == "__main__":
    print_banner()
    print(get_random_quote())
    print("\n" + WEB_PATTERN)
