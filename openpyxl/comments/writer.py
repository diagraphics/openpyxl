from __future__ import absolute_import
# Copyright (c) 2010-2015 openpyxl


from openpyxl.utils.indexed_list import IndexedList
from openpyxl.compat import iteritems
from openpyxl.xml.constants import SHEET_MAIN_NS
from openpyxl.xml.functions import Element, SubElement, tostring, fromstring
from openpyxl.utils import (
    column_index_from_string,
    coordinate_from_string,
)

from .author import AuthorList
from .properties import CommentSheet, Comment

vmlns = "urn:schemas-microsoft-com:vml"
officens = "urn:schemas-microsoft-com:office:office"
excelns = "urn:schemas-microsoft-com:office:excel"


class CommentWriter(object):


    def __init__(self, sheet):
        self.sheet = sheet
        self.comments = []


    def write_comments(self):
        """
        Create list of comments and authors
        Sorted by row, col
        """
        # produce xml
        authors = IndexedList()

        for _coord, cell in sorted(self.sheet._cells.items()):
            if cell.comment is not None:
                comment = Comment(ref=cell.coordinate)
                comment.authorId = authors.add(cell.comment.author)
                comment.text.t = cell.comment.text
                comment.height = cell.comment.height
                comment.width = cell.comment.width
                self.comments.append(comment)

        author_list = AuthorList(authors)
        root = CommentSheet(authors=author_list, commentList=self.comments)

        return tostring(root.to_tree())

    def add_shapetype_vml(self, root):
        shape_layout = SubElement(root, "{%s}shapelayout" % officens,
                                  {"{%s}ext" % vmlns: "edit"})
        SubElement(shape_layout,
                   "{%s}idmap" % officens,
                   {"{%s}ext" % vmlns: "edit", "data": "1"})
        shape_type = SubElement(root,
                                "{%s}shapetype" % vmlns,
                                {"id": "_x0000_t202",
                                 "coordsize": "21600,21600",
                                 "{%s}spt" % officens: "202",
                                 "path": "m,l,21600r21600,l21600,xe"})
        SubElement(shape_type, "{%s}stroke" % vmlns, {"joinstyle": "miter"})
        SubElement(shape_type,
                   "{%s}path" % vmlns,
                   {"gradientshapeok": "t",
                    "{%s}connecttype" % officens: "rect"})
        return root


    def add_shape_vml(self, root, idx, comment):
        shape = _shape_factory()
        col, row = coordinate_from_string(comment.ref)
        row -= 1
        column = column_index_from_string(col) - 1
    
        shape.set('id',  "_x0000_s%04d" % idx)
        client_data = shape.find("{%s}ClientData" % excelns)
        client_data.find("{%s}Row" % excelns).text = str(row)
        client_data.find("{%s}Column" % excelns).text = str(column)
        root.append(shape)

    def write_comments_vml(self):
        sheet = self.sheet
        wb = sheet.parent
        if sheet.legacy_drawing is not None:
            # There is a preserved vml file so we need to merge in the comments
            root = fromstring(wb.vba_archive.read(sheet.legacy_drawing_zip))

            # Remove any existing comment shapes
            while True:
                shape = root.find("{%s}shape[@type='#_x0000_t202']" % vmlns)
                if shape is not None:
                    root.remove(shape)
                else:
                    break
            # Remove the comment shapetype if there is one
            shapetype = root.find("{%s}shapetype[@id='_x0000_t202']" % vmlns)
            if shapetype is not None:
                root.remove(shapetype)
        else:
            root = Element("xml")

        self.add_shapetype_vml(root)
        for idx, comment in enumerate(self.comments, 1026):
            self.add_shape_vml(root, idx, comment)

        return tostring(root)


def _shape_factory():

    style = ("position:absolute; margin-left:59.25pt;"
             "margin-top:1.5pt;width:{width};height:{height};"
             "z-index:1;visibility:hidden").format(height="59.25pt",
                                               width="108pt")
    attrs = {
        "type": "#_x0000_t202",
        "style": style,
        "fillcolor": "#ffffe1",
        "{%s}insetmode" % officens: "auto"
    }
    shape = Element("{%s}shape" % vmlns, attrs)

    SubElement(shape, "{%s}fill" % vmlns,
               {"color2": "#ffffe1"})
    SubElement(shape, "{%s}shadow" % vmlns,
               {"color": "black", "obscured": "t"})
    SubElement(shape, "{%s}path" % vmlns,
               {"{%s}connecttype" % officens: "none"})
    textbox = SubElement(shape, "{%s}textbox" % vmlns,
                         {"style": "mso-direction-alt:auto"})
    SubElement(textbox, "div", {"style": "text-align:left"})
    client_data = SubElement(shape, "{%s}ClientData" % excelns,
                             {"ObjectType": "Note"})
    SubElement(client_data, "{%s}MoveWithCells" % excelns)
    SubElement(client_data, "{%s}SizeWithCells" % excelns)
    SubElement(client_data, "{%s}AutoFill" % excelns).text = "False"
    SubElement(client_data, "{%s}Row" % excelns)
    SubElement(client_data, "{%s}Column" % excelns)
    return shape
