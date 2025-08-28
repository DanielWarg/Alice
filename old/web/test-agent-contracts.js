/**
 * Agent Contract Tests - 3 scenarios for Done-kriterier
 * Test a) "timer.set 10m" → tool_call → tool_result → final
 * Test b) "väder Göteborg" → tool_call → tool_result → final  
 * Test c) felväg: ogiltig tool_result → assisterat degrade-svar (ingen 500)
 */

const API_BASE = 'http://localhost:3001';

async function testAgentContract(testName, userMessage, expectedToolName) {
  console.log(`\n🧪 Test: ${testName}`);
  console.log(`📝 Input: "${userMessage}"`);
  
  try {
    // Step 1: Send user message to agent
    const agentResponse = await fetch(`${API_BASE}/api/agent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: `test_${Date.now()}`,
        messages: [{ role: 'user', content: userMessage }],
        allow_tool_calls: true
      })
    });

    if (!agentResponse.ok) {
      throw new Error(`Agent API returned ${agentResponse.status}`);
    }

    const agentData = await agentResponse.json();
    console.log(`🤖 Agent response: ${agentData.next_action} (${agentData.metrics?.llm_latency_ms}ms)`);

    if (agentData.next_action !== 'tool_call') {
      console.log(`❌ Expected tool_call but got ${agentData.next_action}`);
      return false;
    }

    if (!agentData.assistant.tool_calls || agentData.assistant.tool_calls.length === 0) {
      console.log(`❌ No tool calls returned`);
      return false;
    }

    const toolCall = agentData.assistant.tool_calls[0];
    console.log(`🔧 Tool call: ${toolCall.name} with args:`, toolCall.arguments);

    if (expectedToolName && !toolCall.name.includes(expectedToolName)) {
      console.log(`❌ Expected tool containing '${expectedToolName}' but got '${toolCall.name}'`);
      return false;
    }

    // Step 2: Execute the tool (simulate AgentClient behavior)
    const toolNameMapping = {
      'timer_set': 'timer.set',
      'weather_get': 'weather.get'
    };
    
    const actualToolName = toolNameMapping[toolCall.name] || toolCall.name;
    const toolResponse = await fetch(`${API_BASE}/api/tools/${actualToolName}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(toolCall.arguments)
    });

    if (!toolResponse.ok) {
      console.log(`❌ Tool ${actualToolName} returned ${toolResponse.status}`);
      return false;
    }

    const toolData = await toolResponse.json();
    console.log(`🛠️ Tool result: ${toolData.ok ? 'success' : 'failed'}`);

    // Step 3: Send tool result back to agent for final response
    const finalResponse = await fetch(`${API_BASE}/api/agent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: agentData.session_id,
        messages: [
          { role: 'user', content: userMessage },
          {
            role: 'assistant',
            content: null,
            tool_calls: agentData.assistant.tool_calls.map(tc => ({
              ...tc,
              type: 'function',
              function: { name: tc.name, arguments: JSON.stringify(tc.arguments) }
            }))
          },
          {
            role: 'tool',
            name: toolCall.name,
            tool_call_id: toolCall.id,
            content: JSON.stringify(toolData)
          }
        ],
        allow_tool_calls: true
      })
    });

    if (!finalResponse.ok) {
      throw new Error(`Final agent call returned ${finalResponse.status}`);
    }

    const finalData = await finalResponse.json();
    console.log(`💬 Final response: ${finalData.next_action} - "${finalData.assistant.content?.substring(0, 60)}..."`);

    if (finalData.next_action !== 'final') {
      console.log(`❌ Expected final response but got ${finalData.next_action}`);
      return false;
    }

    console.log(`✅ Test PASSED - Complete tool flow worked`);
    return true;

  } catch (error) {
    console.log(`❌ Test FAILED: ${error.message}`);
    return false;
  }
}

async function testInvalidToolResult() {
  console.log(`\n🧪 Test: Invalid tool result handling`);
  
  try {
    // Step 1: Get a tool call
    const agentResponse = await fetch(`${API_BASE}/api/agent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: `test_invalid_${Date.now()}`,
        messages: [{ role: 'user', content: 'sätt timer 1 minut' }],
        allow_tool_calls: true
      })
    });

    const agentData = await agentResponse.json();
    
    if (agentData.next_action !== 'tool_call') {
      console.log(`❌ Could not get tool_call to test with`);
      return false;
    }

    const toolCall = agentData.assistant.tool_calls[0];

    // Step 2: Send back invalid tool result
    const finalResponse = await fetch(`${API_BASE}/api/agent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: agentData.session_id,
        messages: [
          { role: 'user', content: 'sätt timer 1 minut' },
          {
            role: 'assistant',
            content: null,
            tool_calls: agentData.assistant.tool_calls.map(tc => ({
              ...tc,
              type: 'function',
              function: { name: tc.name, arguments: JSON.stringify(tc.arguments) }
            }))
          },
          {
            role: 'tool',
            name: toolCall.name,
            tool_call_id: toolCall.id,
            content: JSON.stringify({
              ok: false,
              error: { code: 'INVALID', message: 'Simulated tool failure' }
            })
          }
        ],
        allow_tool_calls: true
      })
    });

    if (finalResponse.status >= 500) {
      console.log(`❌ Got 5xx error (${finalResponse.status}) - should degrade gracefully`);
      return false;
    }

    const finalData = await finalResponse.json();
    console.log(`💬 Degraded response: "${finalData.assistant?.content?.substring(0, 60)}..."`);

    if (finalData.next_action === 'final' && finalData.assistant?.content) {
      console.log(`✅ Test PASSED - Graceful degradation without 500 error`);
      return true;
    } else {
      console.log(`❌ Expected graceful degradation with final response`);
      return false;
    }

  } catch (error) {
    console.log(`❌ Test FAILED: ${error.message}`);
    return false;
  }
}

async function runAllTests() {
  console.log('🚀 Starting Agent Contract Tests');
  console.log('=================================');

  const results = [];

  // Test A: Timer tool flow
  results.push(await testAgentContract(
    'Timer 10m → tool_call → tool_result → final',
    'sätt en timer på 10 minuter för lunch',
    'timer'
  ));

  // Test B: Weather tool flow  
  results.push(await testAgentContract(
    'Väder Göteborg → tool_call → tool_result → final',
    'vad är vädret i Göteborg?',
    'weather'
  ));

  // Test C: Invalid tool result handling
  results.push(await testInvalidToolResult());

  console.log('\n📊 Test Results Summary');
  console.log('========================');
  
  const passed = results.filter(r => r).length;
  const total = results.length;
  
  console.log(`✅ Passed: ${passed}/${total}`);
  console.log(`❌ Failed: ${total - passed}/${total}`);
  
  if (passed === total) {
    console.log(`🎉 ALL TESTS PASSED - Agent contracts working correctly!`);
    process.exit(0);
  } else {
    console.log(`💥 Some tests failed - Agent needs fixes`);
    process.exit(1);
  }
}

// Run tests
runAllTests().catch(error => {
  console.error('Test runner crashed:', error);
  process.exit(1);
});