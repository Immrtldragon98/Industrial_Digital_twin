import hashlib
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree
import pandas as pd
from pypdf import PdfReader

WORD_NAMESPACE = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def extract_docx_text(path:Path)->str:
 try:
  with ZipFile(path) as archive:
   xml=archive.read('word/document.xml')
 except (BadZipFile, KeyError) as exc:
  raise ValueError('The DOCX file is invalid or damaged') from exc
 try:
  root=ElementTree.fromstring(xml)
 except ElementTree.ParseError as exc:
  raise ValueError('The DOCX document XML is invalid') from exc
 paragraphs=[]
 for paragraph in root.findall('.//w:p',WORD_NAMESPACE):
  text=''.join(node.text or '' for node in paragraph.findall('.//w:t',WORD_NAMESPACE))
  if text.strip(): paragraphs.append(text)
 return '\n'.join(paragraphs)

def extract_text(path:Path)->str:
 suffix=path.suffix.lower()
 if suffix=='.pdf': return '\n'.join(page.extract_text() or '' for page in PdfReader(str(path)).pages)
 if suffix=='.docx': return extract_docx_text(path)
 if suffix in {'.xlsx','.xls'}:
  book=pd.read_excel(path,sheet_name=None,dtype=str)
  return '\n\n'.join(f'[{name}]\n'+frame.fillna('').to_csv(index=False) for name,frame in book.items())
 if suffix in {'.txt','.md','.csv'}: return path.read_text(encoding='utf-8',errors='replace')
 raise ValueError('Supported files: PDF, DOCX, XLSX, XLS, CSV, TXT, MD')

def chunks(text:str,size:int=1400,overlap:int=180):
 clean='\n'.join(line.strip() for line in text.splitlines() if line.strip())
 result=[]; start=0
 while start<len(clean):
  end=min(len(clean),start+size); cut=clean.rfind('\n',start,end)
  if cut<=start+size//2: cut=end
  result.append(clean[start:cut]); start=max(cut-overlap,start+1)
 return result

def sha256(path:Path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
 return h.hexdigest()

def embed(texts:list[str]):
 import httpx
 from app.core.config import EMBEDDING_MODEL,OLLAMA_URL
 response=httpx.post(f'{OLLAMA_URL}/api/embed',json={'model':EMBEDDING_MODEL,'input':texts},timeout=180)
 response.raise_for_status()
 vectors=response.json()['embeddings']
 if len(vectors)!=len(texts): raise ValueError('Embedding response count does not match input')
 if vectors and len(vectors[0])!=768: raise ValueError(f'Expected 768-dimensional embeddings, received {len(vectors[0])}')
 return vectors
