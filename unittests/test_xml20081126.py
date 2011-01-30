#! /usr/bin/env python

import unittest

from sys import maxunicode
from tempfile import mkdtemp
import shutil, os.path, urllib

MAX_CHAR=0x10FFFF
if maxunicode<MAX_CHAR:
	MAX_CHAR=maxunicode
	print "xml tests truncated to unichr(0x%X) by narrow python build"%MAX_CHAR

def suite():
	return unittest.TestSuite((
		unittest.makeSuite(XML20081126Tests,'test'),
		unittest.makeSuite(XMLDocumentTests,'test'),
		unittest.makeSuite(XMLCharacterTests,'test'),
		unittest.makeSuite(XMLElementTests,'test'),
		unittest.makeSuite(XMLValidationTests,'test')
		))

from pyslet.xml20081126 import *

EXAMPLE_1="""<?xml version="1.0" encoding="utf-8"?>
<tag>Hello World</tag>"""

class XML20081126Tests(unittest.TestCase):		
	def testCaseConstants(self):
		#self.failUnless(APP_NAMESPACE=="http://www.w3.org/2007/app","Wrong APP namespace: %s"%APP_NAMESPACE)
		#self.failUnless(ATOMSVC_MIMETYPE=="application/atomsvc+xml","Wrong APP service mime type: %s"%ATOMSVC_MIMETYPE)
		#self.failUnless(ATOMCAT_MIMETYPE=="application/atomcat+xml","Wrong APP category mime type: %s"%ATOMCAT_MIMETYPE)
		pass

class XMLCharacterTests(unittest.TestCase):
	# Test IsNameChar
	def testChar(self):
		"""[2] Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]"""
		expectedEdges=[0x9,0xB,0xD,0xE,0x20,0xD800,0xE000,0xFFFE,0x10000,0x110000]
		if MAX_CHAR<0x10FFFF:
			expectedEdges=expectedEdges[0:8]
		self.failUnless(self.FindEdges(IsChar,MAX_CHAR)==expectedEdges,"IsChar")

	def testSpace(self):
		"""[3] S ::= (#x20 | #x9 | #xD | #xA)+"""
		expectedEdges=[0x9,0xB,0xD,0xE,0x20,0x21]
		self.failUnless(self.FindEdges(IsSpace,256)==expectedEdges,"IsSpace")
	
	def testNameStart(self):
		"""[4] NameStartChar ::= ":" | [A-Z] | "_" | [a-z] | [#xC0-#xD6] | [#xD8-#xF6] | [#xF8-#x2FF] | [#x370-#x37D] | [#x37F-#x1FFF] | [#x200C-#x200D] | [#x2070-#x218F] | [#x2C00-#x2FEF] | [#x3001-#xD7FF] | [#xF900-#xFDCF] | [#xFDF0-#xFFFD] | [#x10000-#xEFFFF]
		[5] NameChar ::= NameStartChar | "-" | "." | [0-9] | #xB7 | [#x0300-#x036F] | [#x203F-#x2040]"""
		nNameStartChars=0
		nNameChars=0
		for code in xrange(0x10000):
			c=unichr(code)
			if IsNameChar(c):
				nNameChars+=1
				if IsNameStartChar(c):
					nNameStartChars+=1
			else:
				self.failIf(IsNameStartChar(c),"NameStart not a name char: %s"%c)
		self.failUnless(nNameChars==54129,"name char total %i"%nNameChars)
		self.failUnless(nNameStartChars==54002,"name start char total %i"%nNameStartChars)
				
	def testCharClasses(self):
		"""[84] Letter ::= BaseChar | Ideographic
		[85] BaseChar ::= [#x0041-#x005A] | ...
		[86] Ideographic ::= [#x4E00-#x9FA5] | #x3007 | [#x3021-#x3029]
		[87] CombiningChar ::= [#x0300-#x0345] | ...
		[88] Digit ::= [#x0030-#x0039] | ...
		[89] Extender ::= #x00B7 | ..."""
		nBaseChars=0
		nIdeographics=0
		nCombiningChars=0
		nDigits=0
		nExtenders=0
		for code in xrange(0x10000):
			c=unichr(code)
			if IsLetter(c):
				if IsIdeographic(c):
					nIdeographics+=1
				elif IsBaseChar(c):
					nBaseChars+=1
				else:
					self.fail("unichr(%#x) is a letter but not an ideographic or base character"%code)
			else:
				self.failIf(IsIdeographic(c) or IsBaseChar(c),
					"unichr(%#x) is an ideographic or base character but not a letter")
			if IsCombiningChar(c):
				nCombiningChars+=1
			if IsDigit(c):
				nDigits+=1
			if IsExtender(c):
				nExtenders+=1
		self.failUnless(nBaseChars==13602,"base char total %i"%nBaseChars)
		self.failUnless(nIdeographics==20912,"ideographic char total %i"%nIdeographics)
		self.failUnless(nCombiningChars==437,"combing char total %i"%nCombiningChars)
		self.failUnless(nDigits==149,"digit total %i"%nDigits)
		self.failUnless(nExtenders==18,"extender total %i"%nExtenders)

	def FindEdges(self,testFunc,max):
		edges=[]
		flag=False
		for code in xrange(max+1):
			c=unichr(code)
			if flag!=testFunc(c):
				flag=not flag
				edges.append(code)
		return edges

class XMLValidationTests(unittest.TestCase):
	def testCaseName(self):
		self.failUnless(IsValidName("Simple"))
		self.failUnless(IsValidName(":BadNCName"))
		self.failUnless(IsValidName("prefix:BadNCName"))
		self.failUnless(IsValidName("_GoodNCName"))
		self.failIf(IsValidName("-BadName"))
		self.failIf(IsValidName(".BadName"))
		self.failIf(IsValidName("0BadName"))
		self.failUnless(IsValidName("GoodName-0.12"))
		self.failIf(IsValidName("BadName$"))
		self.failIf(IsValidName("BadName+"))
		
class XMLElementTests(unittest.TestCase):
	def testCaseConstructor(self):
		e=XMLElement(None)
		self.failUnless(e.xmlname==None,'element name on construction')
		self.failUnless(e.GetDocument() is None,'document set on construction')
		attrs=e.GetAttributes()
		self.failUnless(len(attrs.keys())==0,"Attributes present on construction")

class XMLDocumentTests(unittest.TestCase):
	def setUp(self):
		self.cwd=os.getcwd()
		self.d=mkdtemp('.d','pyslet-test_xml20081126-')
		os.chdir(self.d)
		
	def tearDown(self):
		os.chdir(self.cwd)
		shutil.rmtree(self.d,True)

	def testCaseConstructor(self):
		d=XMLDocument()
		self.failUnless(d.rootElement is None,'rootElement on construction')
		self.failUnless(d.GetBase() is None,'base set on construction')
		d=XMLDocument(root=XMLElement)
		self.failUnless(isinstance(d.rootElement,XMLElement),'rootElement not created on construction')
		self.failUnless(d.rootElement.GetDocument() is d,'rootElement not linked to document')
		
	def testCaseBase(self):
		"""Test the use of a file path on construction"""
		fpath=os.path.abspath('fpath.xml')
		furl='file://'+urllib.pathname2url(fpath)
		d=XMLDocument(baseURI=urllib.pathname2url(fpath))
		self.failUnless(d.GetBase()==furl,"Base not set in constructor")
		self.failUnless(d.rootElement is None,'rootElement on construction')
		d=XMLDocument(baseURI=urllib.pathname2url('fpath.xml'),root=XMLElement)
		self.failUnless(d.GetBase()==furl,"Base not made absolute from relative URL")
		self.failUnless(isinstance(d.rootElement,XMLElement),'rootElement not created on construction')
		d=XMLDocument()
		d.SetBase(urllib.pathname2url(fpath))
		self.failUnless(d.GetBase()==furl,"Base not set by SetBase")
	
	def testCaseReadFile(self):
		"""Test the reading of the XMLDocument from the file system"""
		f=codecs.open('read1.xml','wb','utf-8')
		f.write(EXAMPLE_1)
		f.close()
		d=XMLDocument(baseURI='read1.xml')
		d.Read()
		root=d.rootElement
		self.failUnless(isinstance(root,XMLElement))
		self.failUnless(root.xmlname=='tag' and root.GetValue()=='Hello World')
		
	def testCaseReadString(self):
		"""Test the reading of the XMLDocument from a supplied stream"""
		d=XMLDocument(baseURI='read2.xml')
		d.Read(src=StringIO(EXAMPLE_1))
		root=d.rootElement
		self.failUnless(isinstance(root,XMLElement))
		self.failUnless(root.xmlname=='tag' and root.GetValue()=='Hello World')
		
	def testCaseCreate(self):
		"""Test the creating of the XMLDocument on the file system"""
		CREATE_1_XML="""<?xml version="1.0" encoding="utf-8"?>
<createTag/>"""
		d=XMLDocument(root=XMLElement)
		d.rootElement.SetXMLName("createTag")
		d.SetBase('create1.xml')
		d.Create()
		try:
			f=open("create1.xml")
			data=f.read()
			f.close()
			self.failUnless(data==CREATE_1_XML,"Create Test")
		except IOError:
			self.fail("Create Test failed to create file")
				
	def testCaseID(self):
		"""Test the built-in handling of a document's ID space."""
		doc=XMLDocument()
		e1=XMLElement(doc)
		e2=XMLElement(doc)
		doc.RegisterElementID(e1,'test')
		try:
			doc.RegisterElementID(e2,'test')
			self.fail("Failed to spot ID clash")
		except XMLIDClashError:
			pass
		doc.RegisterElementID(e2,'test2')
		self.failUnless(doc.GetElementByID('test') is e1,"Element look-up failed")
		newID=doc.GetUniqueID('test')
		self.failIf(newID=='test' or newID=='test2')
		
"""		
class XMLParserTests(unittest.TestCase):
	def testCaseConstructor(self):
		p=XMLParser()
	
	def testCaseExample1(self):
		p=XMLParser()
		doc=p.ParseDocument(EXAMPLE_1)
		self.failUnless(isinstance(doc,XMLDocument))
		root=doc.rootElement
		self.failUnless(isinstance(root,XMLElement))
		self.failUnless(root.xmlname=='tag' and root.GetValue()=='Hello World')
"""

if __name__ == "__main__":
	unittest.main()
