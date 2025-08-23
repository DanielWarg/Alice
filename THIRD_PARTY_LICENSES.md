# Third-Party Licenses

Alice uses open source software. Below are the licenses and copyright information for the third-party dependencies.

## Python Dependencies

### FastAPI and Web Framework
- **FastAPI** - MIT License - Copyright (c) 2018 Sebastián Ramírez
- **Uvicorn** - BSD 3-Clause License - Copyright (c) 2017-present, Encode OSS Ltd.
- **Starlette** - BSD 3-Clause License - Copyright (c) 2018, Encode OSS Ltd.

### HTTP and Networking
- **httpx** - BSD 3-Clause License - Copyright (c) 2019, Encode OSS Ltd.
- **requests** - Apache 2.0 License - Copyright 2019 Kenneth Reitz

### Data Handling and Validation
- **Pydantic** - MIT License - Copyright (c) 2017 to 2019 Samuel Colvin and other contributors
- **orjson** - Apache 2.0 License - Copyright (c) 2018-2021 ijl
- **python-dotenv** - BSD 3-Clause License - Copyright (c) 2014 Saurabh Kumar

### AI and Machine Learning
- **piper-tts** - MIT License - Copyright (c) 2023 Michael Hansen
- **faster-whisper** - MIT License - Copyright (c) 2023 Guillaume Klein
- **cryptography** - Apache 2.0 License - Copyright (c) 2013-2023 The Python Cryptographic Authority

### Google Cloud Integration
- **google-api-python-client** - Apache 2.0 License - Copyright Google Inc.
- **google-auth** - Apache 2.0 License - Copyright Google Inc.
- **google-auth-httplib2** - Apache 2.0 License - Copyright Google Inc.
- **google-auth-oauthlib** - Apache 2.0 License - Copyright Google Inc.

### Testing and Development
- **pytest** - MIT License - Copyright (c) 2004 Holger Krekel and others

### Utilities
- **pytz** - MIT License - Copyright (c) 2003-2005 Stuart Bishop

## Node.js/TypeScript Dependencies

### React and Next.js Framework
- **Next.js** - MIT License - Copyright (c) 2016-present Vercel, Inc.
- **React** - MIT License - Copyright (c) 2013-present, Facebook, Inc.
- **react-dom** - MIT License - Copyright (c) 2013-present, Facebook, Inc.

### UI Components and Styling
- **Radix UI Components** - MIT License - Copyright (c) 2022 WorkOS
  - @radix-ui/react-progress
  - @radix-ui/react-slot  
  - @radix-ui/react-tooltip
- **Lucide React** - ISC License - Copyright (c) 2020, Lucide Contributors
- **Tailwind CSS** - MIT License - Copyright (c) Tailwind Labs, Inc.
- **tailwindcss-animate** - MIT License

### State Management and Utilities
- **Zustand** - MIT License - Copyright (c) 2019 Paul Henschel
- **next-pwa** - MIT License

### Development Tools
- **TypeScript** - Apache 2.0 License - Copyright Microsoft Corporation
- **ESLint** - MIT License - Copyright OpenJS Foundation and other contributors
- **Playwright** - Apache 2.0 License - Copyright Microsoft Corporation
- **Jest** - MIT License - Copyright (c) 2014-present, Facebook, Inc.

## AI Models and External Services

### Speech and Language Models
- **OpenAI Whisper Models** - MIT License - Copyright (c) 2022 OpenAI
- **Piper TTS Voice Models** - Various licenses, primarily permissive
  - Swedish voices (sv_SE-nst-*): Compatible with commercial use
- **Ollama Models** - Various licenses per model
  - Llama 2/3: Custom license allowing commercial use
  - Mistral: Apache 2.0 License

### External API Services
- **Google APIs** - Google APIs Terms of Service
  - Calendar API, Gmail API
  - OAuth 2.0 integration
- **Spotify Web API** - Spotify Developer Terms of Service
  - Music playback control
  - User authentication
- **OpenAI API** - OpenAI Usage Policies
  - Realtime Voice API
  - GPT models

## License Texts

### MIT License
```
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Apache License 2.0
```
Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

1. Definitions.
[Full Apache 2.0 license text would continue here]
```

### BSD 3-Clause License
```
BSD 3-Clause License

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. [Full license text continues...]
```

## Attribution Requirements

### Google Services
When using Google Calendar or Gmail integration:
- "This app uses Google APIs"
- Link to Google Privacy Policy
- Proper OAuth consent screens

### Spotify Integration
When using Spotify features:
- "Spotify" trademark attribution
- Link to Spotify Privacy Policy
- Proper app registration required

### OpenAI Services
When using OpenAI voice features:
- "Powered by OpenAI"
- Compliance with OpenAI usage policies

### Voice Models
- **Piper TTS**: "Text-to-speech powered by Piper"
- **Swedish voices**: Attribution to original voice model creators

## Generating Current License Information

To generate up-to-date license information:

```bash
# For Python dependencies
pip install pip-licenses
pip-licenses --format=markdown

# For Node.js dependencies  
npx license-checker --summary
```

## Commercial Use Notice

All listed dependencies and services have been verified as compatible with commercial use under Alice's MIT license. However, some external services may require:

- **API Keys and Billing**: Google APIs, OpenAI API
- **App Approval**: Spotify for production use
- **Rate Limiting**: Various APIs have usage restrictions
- **Terms Compliance**: Ongoing compliance with service terms

For commercial deployments, please review current service terms and pricing.

---

*This file is maintained as part of Alice's license compliance. Last updated: January 2025*

*For questions about licensing, please refer to LICENSE_COMPLIANCE.md or contact the Alice development team.*