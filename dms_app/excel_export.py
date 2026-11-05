import zipfile
import io
import xml.sax.saxutils as saxutils

def escape_xml(s):
    if s is None:
        return ""
    return saxutils.escape(str(s))

def create_excel_xlsx(headers, rows, sheet_name="DMS Export"):
    """
    Genera un file .xlsx valido al 100% (OpenXML standard ECMA-376)
    usando unicamente zipfile e la standard library di Python,
    garantendo zero dipendenze e zero installazioni.
    """
    output = io.BytesIO()

    # Creazione delle celle in sheet1.xml
    sheet_xml_lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<sheetData>'
    ]

    def col_to_letter(col_idx):
        result = ""
        while col_idx >= 0:
            result = chr(col_idx % 26 + 65) + result
            col_idx = col_idx // 26 - 1
        return result

    # Riga 1: Intestazioni
    row_idx = 1
    sheet_xml_lines.append(f'<row r="{row_idx}">')
    for c_idx, h in enumerate(headers):
        ref = f"{col_to_letter(c_idx)}{row_idx}"
        val = escape_xml(h)
        sheet_xml_lines.append(f'<c r="{ref}" t="inlineStr"><is><t>{val}</t></is></c>')
    sheet_xml_lines.append('</row>')

    # Righe dati
    for row_data in rows:
        row_idx += 1
        sheet_xml_lines.append(f'<row r="{row_idx}">')
        for c_idx, val in enumerate(row_data):
            ref = f"{col_to_letter(c_idx)}{row_idx}"
            escaped_val = escape_xml(val)
            sheet_xml_lines.append(f'<c r="{ref}" t="inlineStr"><is><t>{escaped_val}</t></is></c>')
        sheet_xml_lines.append('</row>')

    sheet_xml_lines.append('</sheetData>')
    sheet_xml_lines.append('</worksheet>')
    sheet_xml_content = "\n".join(sheet_xml_lines)

    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
    <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

    root_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    workbook_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <sheets>
        <sheet name="{escape_xml(sheet_name)}" sheetId="1" r:id="rId1"/>
    </sheets>
</workbook>"""

    workbook_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml_content)

    return output.getvalue()
