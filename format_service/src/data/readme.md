# Data Preparation for Record Class

## Overview

This document outlines the necessary steps to prepare raw data for ingestion into the `Record` class. Properly formatted data is essential for creating valid instances of the `Record` class and ensuring that they function as intended in the application.

## Data Structure

The `Record` class have the following fields:

- `record_id`: (string) A unique identifier for the record. If not provided, it will be generated.
- `document_id`: (string, optional) A unique identifier for the source document.
- `title`: (string) The title or summary of the record.
- `content`: (string) The main content used for Retrieval-Augmented Generation (RAG).
- `chunk_id`: (string, optional) A unique identifier for each content chunk.
- `hierarchy_level`: (integer, optional) The structural level of the content.
- `categories`: (list of strings, optional) A list of categories or tags assigned to the record.
- `relationships`: (list of strings, optional) A list of relationships with other records.
- `published_date`: (string, optional) The publication or creation date.
- `source`: (string, optional) The origin of the record.
- `processing_timestamp`: (string, optional) The timestamp when the record was processed.
- `validation_status`: (boolean, optional) Indicates if the record passed validation checks.
- `language`: (string, optional) The language of the content (default is 'vi').
- `summary`: (string, optional) A brief overview of the content.

### Example JSON Structure

To ingest data into the `Record` class, prepare your raw data in JSON or tagged format. Below is an example of a properly formatted JSON object:

```json
{
  "record_id": "QA_FBCD2A6F",
  "document_id": "N/A",
  "title": "Thủ tục cấp Giấy chứng nhận ATTP nấm Đông Trùng Hạ Thảo",
  "content": "GIẤY CHỨNG NHẬN ATTP NẤM ĐÔNG TRÙNG HẠ THẢO\nI/ Khái niệm ...",
  "chunk_id": "N/A",
  "hierarchy_level": 1,
  "categories": ["Dịch Vụ Pháp Lý", "Giấy Phép Con"],
  "relationships": [],
  "published_date": "April 8, 2020",
  "source": null,
  "processing_timestamp": "2024-09-28T14:41:15.122550",
  "validation_status": false,
  "language": "vi",
  "summary": ""
}
```
Below is an expample of a tagged object:

```tagged
<id=QA1>
<title>Thủ tục cấp Giấy chứng nhận ATTP nấm Đông Trùng Hạ Thảo</title>
<published_date>April 8, 2020</published_date>
<categories><Dịch Vụ Pháp Lý><Giấy Phép Con></categories>
<content>GIẤY CHỨNG NHẬN ATTP NẤM ĐÔNG TRÙNG HẠ THẢO\nI/ Khái niệm ...
</content>
</id=QA1>
```
### Raw text ingestion
The module can handle raw text (.doc, .txt) files by chunking them into smaller chunks and automatically assigning an ID, and a title to each chunk. However, this is not recommended as it is only in early development for the chunking algorithm
