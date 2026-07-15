"""Artwork-Binder-Generator.

Vollautomatische Pipeline: Kartenfoto -> Analyse -> Prompt -> KI-Bild ->
9-Kachel-Zuschnitt -> druckfertiges A4/Letter-PDF.

Die einzelnen Schritte liegen in getrennten Modulen, damit sich jeder
Zwischenschritt (erkannter Typ, Prompt, Rohbild) einzeln nachvollziehen
und bei Bedarf manuell korrigieren laesst.
"""

__version__ = "1.0.0"
