"""
Security layer
InputSanitizer class to check and clean user input, preventing injection attacks ,
PII detection /masking, output validation.
"""

import re
from typing import Optional
from langsmith import traceable

class InputSanitizer:
    """Sanitizes input to prevent injection attacks and ensure data integrity."""
    
    INJECTION_PATTERNS = [
        r"(?i)\b("
        r"ignore\s+(all\s+)?previous\s+instructions|"
        r"disregard\s+(all\s+)?(prior|previous)\s+instructions|"
        r"forget\s+(all\s+)?previous\s+instructions|"
        r"system\s+prompt|"
        r"reveal\s+your\s+instructions|"
        r"show\s+your\s+prompt|"
        r"print\s+your\s+instructions|"
        r"developer\s+message|"
        r"assistant\s+instructions|"
        r"jailbreak|"
        r"do\s+not\s+follow\s+previous\s+instructions|"
        r"override\s+your\s+instructions|"
        r"act\s+as\s+an?\s+unrestricted\s+ai|"
        r"you\s+are\s+now\s+.*|"
        r"begin\s+new\s+system\s+prompt|"
        r"new\s+instructions\s*:|"
        r"<\s*system\s*>|"
        r"</\s*system\s*>|"
        r"<\s*assistant\s*>|"
        r"</\s*assistant\s*>"
        r")\b"
    ]

    def __init__(self):
        self.patterns = [
            re.compile(p,re.IGNORECASE)
            for p in self.INJECTION_PATTERNS 
        ]
    
    def check(self,text:str) -> tuple[bool,Optional[str]]:
        """
        Check if input is safe .
        Returns :(is_safe,rejection_reason)
        """
        for pattern in self.patterns:
            if pattern.search(text):
                return False, f"Input contains potentially harmful pattern: '{pattern.pattern}'"
        return True,None
    
    def clean(self,text:str) -> str:
        """
        Clean input by removing potentially harmful patterns.
        """
        text = re.sub(r'[-]{3,}', '', text)
        text = re.sub(r'[=]{3,}', '', text)
        text = text.replace('{{','{ {').replace('}}','} }')
        return text.strip()


class PIIDetector:
    """Detects and masks personally identifiable information (PII) in text."""
    
    PII_PATTERNS = {
        "email": re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'),
        "phone": re.compile(r'\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b'),
        "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        "credit_card": re.compile(r'\b(?:\d[ -]*?){13,16}\b')
    }

    MASK_MAP = {
        "email": "[REDACTED_EMAIL]",
        "phone": "[REDACTED_PHONE]",
        "ssn": "[REDACTED_SSN]",
        "credit_card": "[REDACTED_CREDIT_CARD]"
    }

    def detect(self,text:str) -> dict[str,list[str]]:
        """Detect PII in the input text."""
        found = {}
        for key, pattern in self.PII_PATTERNS.items():
            matches = pattern.findall(text)
            if matches: 
                found[key] = matches
        return found
    
    def mask(self,text:str) -> str:
        """Mask detected PII in the input text."""
        masked=text
        for pii,pattern in self.PII_PATTERNS.items():
            masked = pattern.sub(self.MASK_MAP[pii], masked)
        return masked
    
    
class OutputValidator:
    """
    Validates LLM output before returning to the client.
    Catches PII leakage and harmful content in response
    """

    HARMFUL_PATTERNS = [
        r"(?i)\b("
        r"ignore\s+(all\s+)?previous\s+instructions|"
        r"disregard\s+(all\s+)?(prior|previous)\s+instructions|"
        r"forget\s+(all\s+)?previous\s+instructions|"
        r"system\s+prompt|"
        r"reveal\s+your\s+instructions|"
        r"show\s+your\s+prompt|"
        r"print\s+your\s+instructions|"
        r"developer\s+message|"
        r"assistant\s+instructions|"
        r"jailbreak|"
        r"do\s+not\s+follow\s+previous\s+instructions|"
        r"override\s+your\s+instructions|"
        r"act\s+as\s+an?\s+unrestricted\s+ai|"
        r"you\s+are\s+now\s+.*|"
        r"begin\s+new\s+system\s+prompt|"
        r"new\s+instructions\s*:|"
        r"<\s*system\s*>|"
        r"</\s*system\s*>|"
        r"<\s*assistant\s*>|"
        r"</\s*assistant\s*>"
        r")\b"
    ]

    def __init__(self):
        self.pii_detector = PIIDetector()

    def validate(self,output:str)-> tuple[str,list[str]]:
        """Validate output for harmful content and PII leakage
        . Returns (validated_output,issues)"""
        issues = []

        #Check for harmful patterns
        for pattern in self.HARMFUL_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                issues.append(f"Output contains potentially harmful pattern: '{pattern}'")
        
        #Check for PII leakage
        pii_found = self.pii_detector.detect(output)
        if pii_found:
            issues.append(f"Output contains potential PII: {pii_found}")
            output = self.pii_detector.mask(output)
            
        return output,issues
    




class SecurityPipeline:
    """
    Full security pipeline that process input and output.
    This is the single class you are wire into your API.
    """

    def __init__(self):
        self.input_sanitizer = InputSanitizer()
        self.pii_detector = PIIDetector()
        self.output_validator = OutputValidator()

    @traceable(name = "security_pipeline_input_check")
    def check_input(self,user_input:str) -> tuple[bool,str,list[str]]:
        """Process input through the security pipeline.
        Returns (is_safe,reason,issues)"""
        issues = []

        #Step1-Check for Prompt Injection 
        is_safe,reason = self.input_sanitizer.check(user_input)
        
        if not is_safe:
            issues.append(f"Input rejected: {reason}")
            return False, "Input rejected due to security concerns.", issues
        
        #Step2-Clean the input
        cleaned = self.input_sanitizer.clean(user_input)


        #Step3 : Mask PII before it reaches the llm
        pii_found = self.pii_detector.detect(cleaned)
        if pii_found:
            issues.append(f"Input contains potential PII: {pii_found}")
            cleaned = self.pii_detector.mask(cleaned)

        return True, cleaned, issues
    
    @traceable(name = "security_pipeline_output_check")
    def validate_output(self,output:str) -> tuple[bool,str,list[str]]:
        """Process output through the security pipeline.
        Returns (is_valid,validated_output,issues)"""
        validated_output,issues = self.output_validator.validate(output)
        is_valid = len(issues) == 0
        return is_valid, validated_output, issues
    