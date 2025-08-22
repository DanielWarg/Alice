#!/usr/bin/env python3
"""
NLU Stresstest för Alice
Testar intent classification under belastning och verifierar precision/recall
"""

import os
import time
import json
import random
import statistics
from concurrent.futures import ThreadPoolExecutor
from core.router import classify, get_router_stats, ROUTER_RULES
from core.tool_specs import enabled_tools

# Enable all tools for testing
os.environ["ENABLED_TOOLS"] = ",".join(ROUTER_RULES.keys())

# Test cases för varje tool med expected confidence
TEST_CASES = {
    "PLAY": [
        ("spela upp", 1.0),
        ("starta musik", 0.95),
        ("play", 1.0), 
        ("fortsätt spela", 1.0),
        ("spela", 1.0),
        ("spela music", 0.9),  # Mixed language
        ("kan du spela upp", 0.85),  # Natural language
    ],
    "PAUSE": [
        ("pausa", 1.0),
        ("pause", 1.0),
        ("stoppa tillfälligt", 1.0),
        ("paus", 0.9),
        ("pausa musiken", 1.0),
    ],
    "STOP": [
        ("stoppa", 1.0),
        ("stop", 1.0),
        ("avsluta", 1.0),
        ("stoppa musiken", 1.0),
        ("stopp", 0.9),
    ],
    "NEXT": [
        ("nästa", 1.0),
        ("next", 1.0),
        ("nästa låt", 1.0),
        ("hoppa framåt", 1.0),
        ("skip", 1.0),
    ],
    "PREV": [
        ("föregående", 1.0),
        ("previous", 1.0),
        ("föregående låt", 1.0),
        ("gå tillbaka", 1.0),
        ("prev", 1.0),
    ],
    "SET_VOLUME": [
        ("sätt volym till 50%", 0.95),
        ("volym 80", 0.95),
        ("höj volym med 10%", 0.95),
        ("sänk volymen med 20", 0.95),
        ("volym 100%", 0.95),
        ("höj volymen", 0.8),
        ("sänk volym", 0.8),
        ("sätt volym till 0", 0.95),
    ],
    "MUTE": [
        ("mute", 1.0),
        ("stäng av ljudet", 1.0),
        ("ljud av", 1.0),
        ("tyst", 1.0),
    ],
    "UNMUTE": [
        ("unmute", 1.0),
        ("sätt på ljudet", 1.0),
        ("ljud på", 1.0),
        ("ljud tillbaka", 1.0),
    ],
    "SHUFFLE": [
        ("shuffle", 1.0),
        ("blanda", 1.0),
        ("blanda låtar", 1.0),
        ("slumpvis", 1.0),
    ],
    "LIKE": [
        ("gilla", 1.0),
        ("like", 1.0),
        ("gilla låten", 1.0),
        ("favorit", 1.0),
        ("spara låt", 1.0),
    ],
    "UNLIKE": [
        ("ogilla", 1.0),
        ("unlike", 1.0),
        ("ta bort favorit", 1.0),
        ("ta bort från favoriter", 1.0),
    ]
}

# Negative test cases - should NOT match any tool
NEGATIVE_CASES = [
    "hej alice",
    "vad heter du", 
    "berätta en skämt",
    "hur mår du",
    "vad är klockan",
    "väder idag",
    "skicka ett mail",  # Gmail tool, not in router
    "läs mina mail",    # Gmail tool, not in router
    "random text here",
    "asd123fgh",
    "",
    "   ",
    "this should not match anything at all",
]

# Edge cases - tricky inputs
EDGE_CASES = [
    ("spela upp något", 0.85),  # Natural language
    ("kan du starta musiken", 0.8),  # Natural language  
    ("höj lite på volymen", 0.7),  # Fuzzy volume
    ("paussa", 0.8),  # Typo
    ("nasta", 0.8),   # Missing accent
    ("föregaende", 0.8),  # Typo
    ("shuffel", 0.8), # Typo
    ("gillar", 0.8),  # Different form
    ("spela något bra", 0.7),  # Extra words
]

class NLUStressTest:
    def __init__(self):
        self.results = {
            'classification_times': [],
            'correct_classifications': 0,
            'incorrect_classifications': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'errors': [],
            'confidence_scores': [],
            'tool_performance': {}
        }
        
    def test_positive_cases(self):
        """Test alla positiva test cases"""
        print("✅ Testar positiva cases...")
        
        for tool_name, test_cases in TEST_CASES.items():
            if tool_name not in self.results['tool_performance']:
                self.results['tool_performance'][tool_name] = {
                    'correct': 0, 'incorrect': 0, 'times': []
                }
            
            for text, expected_confidence in test_cases:
                try:
                    t0 = time.time()
                    result = classify(text)
                    classification_time = time.time() - t0
                    
                    self.results['classification_times'].append(classification_time)
                    self.results['tool_performance'][tool_name]['times'].append(classification_time)
                    
                    if result and result.get('tool') == tool_name:
                        self.results['correct_classifications'] += 1
                        self.results['tool_performance'][tool_name]['correct'] += 1
                        
                        confidence = result.get('confidence', 0)
                        self.results['confidence_scores'].append(confidence)
                        
                        # Warn if confidence is much lower than expected
                        if confidence < expected_confidence - 0.1:
                            print(f"⚠️  Low confidence: '{text}' -> {confidence:.2f} (expected {expected_confidence:.2f})")
                            
                    else:
                        self.results['incorrect_classifications'] += 1
                        self.results['tool_performance'][tool_name]['incorrect'] += 1
                        self.results['false_negatives'] += 1
                        print(f"❌ False negative: '{text}' -> {result}")
                        
                except Exception as e:
                    self.results['errors'].append(f"Error classifying '{text}': {e}")
    
    def test_negative_cases(self):
        """Test negativa cases - ska INTE matcha något tool"""
        print("\n❌ Testar negativa cases...")
        
        for text in NEGATIVE_CASES:
            try:
                t0 = time.time()
                result = classify(text)
                classification_time = time.time() - t0
                
                self.results['classification_times'].append(classification_time)
                
                if result is None:
                    # Korrekt - ingen match
                    pass
                else:
                    # False positive
                    self.results['false_positives'] += 1
                    print(f"❌ False positive: '{text}' -> {result}")
                    
            except Exception as e:
                self.results['errors'].append(f"Error with negative case '{text}': {e}")
    
    def test_edge_cases(self):
        """Test edge cases - svåra/tvetydiga inputs"""
        print("\n🤔 Testar edge cases...")
        
        for text, min_confidence in EDGE_CASES:
            try:
                t0 = time.time() 
                result = classify(text)
                classification_time = time.time() - t0
                
                self.results['classification_times'].append(classification_time)
                
                if result:
                    confidence = result.get('confidence', 0)
                    self.results['confidence_scores'].append(confidence)
                    
                    if confidence >= min_confidence:
                        print(f"✅ Edge case OK: '{text}' -> {result['tool']} ({confidence:.2f})")
                    else:
                        print(f"⚠️  Edge case low confidence: '{text}' -> {confidence:.2f}")
                else:
                    print(f"❓ Edge case no match: '{text}'")
                    
            except Exception as e:
                self.results['errors'].append(f"Error with edge case '{text}': {e}")
    
    def test_concurrent_classification(self):
        """Test concurrent classification load"""
        print("\n⚡ Testar concurrent classification...")
        
        # Skapa en stor pool av test inputs
        all_texts = []
        for test_cases in TEST_CASES.values():
            all_texts.extend([text for text, _ in test_cases])
        all_texts.extend(NEGATIVE_CASES)
        all_texts.extend([text for text, _ in EDGE_CASES])
        
        # Duplicera för mer load
        test_pool = all_texts * 5  # 5x varje test
        random.shuffle(test_pool)
        
        def worker_task(texts):
            worker_results = {'times': [], 'errors': []}
            for text in texts:
                try:
                    t0 = time.time()
                    result = classify(text)
                    worker_results['times'].append(time.time() - t0)
                except Exception as e:
                    worker_results['errors'].append(f"Worker error: {e}")
            return worker_results
        
        # Dela upp work mellan threads
        chunk_size = len(test_pool) // 10
        chunks = [test_pool[i:i+chunk_size] for i in range(0, len(test_pool), chunk_size)]
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_task, chunk) for chunk in chunks]
            worker_results = [f.result() for f in futures]
        
        total_time = time.time() - start_time
        
        # Samla resultat
        all_times = []
        all_errors = []
        for result in worker_results:
            all_times.extend(result['times'])
            all_errors.extend(result['errors'])
        
        self.results['errors'].extend(all_errors)
        
        print(f"🔄 10 workers, {len(all_times)} classifications på {total_time:.2f}s")
        if all_times:
            avg_time = statistics.mean(all_times)
            max_time = max(all_times)
            throughput = len(all_times) / total_time
            print(f"📊 Genomsnitt: {avg_time*1000:.1f}ms, Max: {max_time*1000:.1f}ms")
            print(f"📈 Throughput: {throughput:.1f} classifications/sec")
    
    def test_router_robustness(self):
        """Test router med extrema inputs"""
        print("\n🛡️  Testar router robusthet...")
        
        extreme_inputs = [
            None,
            "",
            "   ",
            "a" * 1000,  # Very long string
            "åäö" * 100,  # Unicode stress
            "!@#$%^&*()",  # Special chars
            "123456789",   # Numbers only
            "\n\t\r",      # Whitespace chars
            "spela" * 50,  # Repeated word
        ]
        
        for text in extreme_inputs:
            try:
                t0 = time.time()
                result = classify(text)
                classification_time = time.time() - t0
                
                # Should not crash
                if classification_time > 0.01:  # > 10ms is slow for extreme case
                    print(f"⚠️  Slow extreme case: {classification_time*1000:.1f}ms for {repr(text[:20])}")
                    
            except Exception as e:
                self.results['errors'].append(f"Extreme input error: {e}")
                print(f"💥 Crash on extreme input: {repr(text[:20])}")
    
    def performance_analysis(self):
        """Analysera NLU prestanda"""
        print("\n📊 NLU PRESTANDA ANALYS")  
        print("=" * 50)
        
        # Overall metrics
        total_tests = self.results['correct_classifications'] + self.results['incorrect_classifications']
        if total_tests > 0:
            accuracy = self.results['correct_classifications'] / total_tests
            print(f"🎯 Accuracy: {accuracy:.2%} ({self.results['correct_classifications']}/{total_tests})")
        
        print(f"❌ False Positives: {self.results['false_positives']}")
        print(f"❌ False Negatives: {self.results['false_negatives']}")
        
        # Timing stats
        if self.results['classification_times']:
            times = self.results['classification_times']
            avg_time = statistics.mean(times)
            max_time = max(times)
            min_time = min(times)
            p95_time = sorted(times)[int(0.95 * len(times))]
            
            print(f"\n⏱️  Timing:")
            print(f"   Genomsnitt: {avg_time*1000:.2f}ms")
            print(f"   Min/Max: {min_time*1000:.2f}ms / {max_time*1000:.2f}ms") 
            print(f"   95th percentile: {p95_time*1000:.2f}ms")
            print(f"   Total tests: {len(times)}")
        
        # Confidence stats
        if self.results['confidence_scores']:
            confidences = self.results['confidence_scores']
            avg_conf = statistics.mean(confidences)
            min_conf = min(confidences)
            
            print(f"\n🎯 Confidence:")
            print(f"   Genomsnitt: {avg_conf:.3f}")
            print(f"   Minimum: {min_conf:.3f}")
            print(f"   Samples: {len(confidences)}")
        
        # Per-tool performance
        print(f"\n🔧 Per-tool prestanda:")
        for tool, perf in self.results['tool_performance'].items():
            if perf['correct'] + perf['incorrect'] > 0:
                tool_accuracy = perf['correct'] / (perf['correct'] + perf['incorrect'])
                avg_time = statistics.mean(perf['times']) if perf['times'] else 0
                print(f"   {tool}: {tool_accuracy:.2%} accuracy, {avg_time*1000:.2f}ms avg")
        
        # Errors
        if self.results['errors']:
            print(f"\n❌ FEL: {len(self.results['errors'])} fel:")
            for error in self.results['errors'][:3]:
                print(f"   - {error}")
            if len(self.results['errors']) > 3:
                print(f"   ... och {len(self.results['errors'])-3} till")
        else:
            print(f"\n✅ Inga fel!")
        
        # Router stats
        router_stats = get_router_stats()
        print(f"\n📋 Router info:")
        print(f"   Tools: {router_stats['enabled_tools']}/{router_stats['total_tools']} aktiva")
        print(f"   Synonymer: {router_stats['total_synonyms']} totalt")
        print(f"   Aktiva tools: {', '.join(router_stats['enabled_tools_list'])}")
    
    def run_all_tests(self):
        """Kör alla NLU-tester"""
        print("🧠 ALICE NLU STRESSTEST STARTAR")
        print("=" * 50)
        
        start_time = time.time()
        
        self.test_positive_cases()
        self.test_negative_cases()
        self.test_edge_cases()
        self.test_concurrent_classification()
        self.test_router_robustness()
        
        total_time = time.time() - start_time
        print(f"\n⏱️  Total NLU testtid: {total_time:.2f}s")
        
        self.performance_analysis()

if __name__ == "__main__":
    test = NLUStressTest()
    test.run_all_tests()