#!/usr/bin/env python3
"""
Backend API Test Suite for DSA Interview Assistant
Tests all API endpoints with realistic DSA questions and scenarios
"""

import requests
import json
import time
from typing import Dict, Any, Optional

# Get backend URL from frontend .env
BACKEND_URL = "https://listen-respond-3.preview.emergentagent.com/api"

class DSAInterviewTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str, response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        if response_data and not success:
            print(f"   Response: {response_data}")
    
    def test_root_endpoint(self):
        """Test the root API endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                if "DSA Interview Assistant API" in data.get("message", ""):
                    self.log_test("Root Endpoint", True, "API root accessible and returns correct message")
                else:
                    self.log_test("Root Endpoint", False, f"Unexpected message: {data}", data)
            else:
                self.log_test("Root Endpoint", False, f"Status code: {response.status_code}", response.text)
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Connection error: {str(e)}")
    
    def test_ask_simple_question(self) -> Optional[str]:
        """Test POST /api/ask with a simple DSA question"""
        try:
            question_data = {
                "question": "What is binary search and what is its time complexity?"
            }
            
            response = self.session.post(
                f"{self.base_url}/ask",
                json=question_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["answer", "conversation_id", "message_id"]
                
                if all(field in data for field in required_fields):
                    if len(data["answer"]) > 50:  # Reasonable answer length
                        self.log_test("Simple DSA Question", True, 
                                    f"Got valid response with {len(data['answer'])} chars")
                        return data["conversation_id"]
                    else:
                        self.log_test("Simple DSA Question", False, 
                                    f"Answer too short: {data['answer']}", data)
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_test("Simple DSA Question", False, 
                                f"Missing fields: {missing}", data)
            else:
                self.log_test("Simple DSA Question", False, 
                            f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Simple DSA Question", False, f"Error: {str(e)}")
        
        return None
    
    def test_ask_code_question(self) -> Optional[str]:
        """Test POST /api/ask with a coding question"""
        try:
            question_data = {
                "question": "Write a Python function to implement binary search on a sorted array"
            }
            
            response = self.session.post(
                f"{self.base_url}/ask",
                json=question_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "")
                
                # Check if response contains code (look for common code indicators)
                has_code = any(indicator in answer.lower() for indicator in 
                             ["def ", "function", "```", "python", "return"])
                
                if has_code and len(answer) > 100:
                    self.log_test("Code Question", True, 
                                f"Got code response with {len(answer)} chars")
                    return data["conversation_id"]
                else:
                    self.log_test("Code Question", False, 
                                f"Response doesn't contain expected code: {answer[:200]}...", data)
            else:
                self.log_test("Code Question", False, 
                            f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Code Question", False, f"Error: {str(e)}")
        
        return None
    
    def test_follow_up_question(self, conversation_id: str):
        """Test follow-up question with existing conversation_id"""
        if not conversation_id:
            self.log_test("Follow-up Question", False, "No conversation_id provided")
            return
            
        try:
            question_data = {
                "question": "Can you optimize that binary search function further?",
                "conversation_id": conversation_id
            }
            
            response = self.session.post(
                f"{self.base_url}/ask",
                json=question_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("conversation_id") == conversation_id:
                    self.log_test("Follow-up Question", True, 
                                "Successfully maintained conversation context")
                else:
                    self.log_test("Follow-up Question", False, 
                                f"Conversation ID mismatch: expected {conversation_id}, got {data.get('conversation_id')}", data)
            else:
                self.log_test("Follow-up Question", False, 
                            f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Follow-up Question", False, f"Error: {str(e)}")
    
    def test_get_conversations(self):
        """Test GET /api/conversations"""
        try:
            response = self.session.get(f"{self.base_url}/conversations")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Get Conversations", True, 
                                f"Retrieved {len(data)} conversations")
                    return data
                else:
                    self.log_test("Get Conversations", False, 
                                f"Expected list, got: {type(data)}", data)
            else:
                self.log_test("Get Conversations", False, 
                            f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Get Conversations", False, f"Error: {str(e)}")
        
        return []
    
    def test_get_specific_conversation(self, conversation_id: str):
        """Test GET /api/conversations/{conversation_id}"""
        if not conversation_id:
            self.log_test("Get Specific Conversation", False, "No conversation_id provided")
            return
            
        try:
            response = self.session.get(f"{self.base_url}/conversations/{conversation_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("id") == conversation_id and "messages" in data:
                    message_count = len(data.get("messages", []))
                    self.log_test("Get Specific Conversation", True, 
                                f"Retrieved conversation with {message_count} messages")
                else:
                    self.log_test("Get Specific Conversation", False, 
                                f"Invalid conversation data structure", data)
            elif response.status_code == 404:
                self.log_test("Get Specific Conversation", False, 
                            "Conversation not found (404)", response.text)
            else:
                self.log_test("Get Specific Conversation", False, 
                            f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Get Specific Conversation", False, f"Error: {str(e)}")
    
    def test_delete_conversation(self, conversation_id: str):
        """Test DELETE /api/conversations/{conversation_id}"""
        if not conversation_id:
            self.log_test("Delete Conversation", False, "No conversation_id provided")
            return
            
        try:
            response = self.session.delete(f"{self.base_url}/conversations/{conversation_id}")
            
            if response.status_code == 200:
                data = response.json()
                if "deleted successfully" in data.get("message", "").lower():
                    self.log_test("Delete Conversation", True, "Conversation deleted successfully")
                else:
                    self.log_test("Delete Conversation", False, 
                                f"Unexpected delete response: {data}", data)
            elif response.status_code == 404:
                self.log_test("Delete Conversation", False, 
                            "Conversation not found for deletion (404)", response.text)
            else:
                self.log_test("Delete Conversation", False, 
                            f"Status code: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Delete Conversation", False, f"Error: {str(e)}")
    
    def test_error_handling(self):
        """Test various error conditions"""
        
        # Test empty question
        try:
            response = self.session.post(
                f"{self.base_url}/ask",
                json={"question": ""},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [400, 422]:
                self.log_test("Empty Question Error", True, "Properly rejected empty question")
            else:
                self.log_test("Empty Question Error", False, 
                            f"Should reject empty question, got status: {response.status_code}")
        except Exception as e:
            self.log_test("Empty Question Error", False, f"Error: {str(e)}")
        
        # Test invalid conversation ID
        try:
            response = self.session.post(
                f"{self.base_url}/ask",
                json={
                    "question": "Test question",
                    "conversation_id": "invalid-uuid-12345"
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [404, 400]:
                self.log_test("Invalid Conversation ID", True, "Properly handled invalid conversation ID")
            else:
                self.log_test("Invalid Conversation ID", False, 
                            f"Should handle invalid conversation ID, got status: {response.status_code}")
        except Exception as e:
            self.log_test("Invalid Conversation ID", False, f"Error: {str(e)}")
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting DSA Interview Assistant Backend Tests")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test basic connectivity
        self.test_root_endpoint()
        
        # Test core functionality
        conversation_id1 = self.test_ask_simple_question()
        conversation_id2 = self.test_ask_code_question()
        
        # Test follow-up (use first conversation if available)
        if conversation_id1:
            self.test_follow_up_question(conversation_id1)
        
        # Test conversation retrieval
        conversations = self.test_get_conversations()
        
        # Test specific conversation retrieval
        if conversation_id1:
            self.test_get_specific_conversation(conversation_id1)
        
        # Test error handling
        self.test_error_handling()
        
        # Test deletion (use second conversation to preserve first for follow-up tests)
        if conversation_id2:
            self.test_delete_conversation(conversation_id2)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        return self.test_results

if __name__ == "__main__":
    tester = DSAInterviewTester()
    results = tester.run_all_tests()