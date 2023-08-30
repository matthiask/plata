from pdfdocument.document import PDFDocument
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import plata


def init_regular_font(suffix=""):
    name = f"{plata.settings.PLATA_PDF_FONT_NAME}{suffix}"
    path = plata.settings.PLATA_PDF_FONT_PATH or "%s.ttf" % name
    pdfmetrics.registerFont(TTFont(name, path))


class PlataPDFDocument(PDFDocument):
    def __init__(self, *args, **kwargs):
        if plata.settings.PLATA_PDF_FONT_NAME:
            init_regular_font()
            # add font name as parametr to parent PDFDocument class
            kwargs["font_name"] = plata.settings.PLATA_PDF_FONT_NAME

        if plata.settings.PLATA_PDF_FONT_BOLD_NAME:
            # init bold font variant
            name = plata.settings.PLATA_PDF_FONT_BOLD_NAME
            path = plata.settings.PLATA_PDF_FONT_BOLD_PATH or "%s.ttf" % name
            pdfmetrics.registerFont(TTFont(name, path))
        elif plata.settings.PLATA_PDF_FONT_NAME:
            # init bold font variant from regular font, bold is always needed
            init_regular_font(suffix="-Bold")

        super().__init__(*args, **kwargs)
