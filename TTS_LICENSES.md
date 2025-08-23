# Alice TTS Licensing and Attribution

This document provides comprehensive licensing information for all Text-to-Speech (TTS) components used in Alice AI Assistant.

## Summary

Alice's Swedish TTS system uses Piper TTS engine with Swedish voice models. All components are licensed under open source licenses that permit commercial use with proper attribution.

✅ **Commercial Use Allowed**  
✅ **Distribution Permitted**  
✅ **Modification Permitted**  
⚠️ **Attribution Required**

---

## Voice Models

### NST Swedish Voice Models

**Models:** `sv_SE-nst-medium.onnx`, `sv_SE-nst-high.onnx`

**Dataset:** Norwegian Speech Technology (NST) Swedish Speech Database  
**Source:** Norwegian Language Bank  
**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)  
**License URL:** https://creativecommons.org/licenses/by/4.0/  
**Dataset URL:** https://www.nb.no/sprakbanken/en/resource-catalogue/oai-nb-no-sbr-56/

#### License Terms
- ✅ Commercial use permitted
- ✅ Distribution permitted  
- ✅ Modification permitted
- ✅ Private use permitted
- ⚠️ Attribution required
- ⚠️ License notice must be included

#### Required Attribution
```
Voice models based on NST Swedish Speech Database 
(https://www.nb.no/sprakbanken/)
Licensed under CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/)
Processed using Piper TTS (https://github.com/rhasspy/piper)
```

### Lisa Swedish Voice Models

**Models:** `sv_SE-lisa-medium.onnx`

**Dataset:** Lisa Swedish TTS Dataset  
**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)  
**License URL:** https://creativecommons.org/licenses/by/4.0/

#### License Terms
- ✅ Commercial use permitted
- ✅ Distribution permitted
- ✅ Modification permitted  
- ✅ Private use permitted
- ⚠️ Attribution required
- ⚠️ License notice must be included

#### Required Attribution
```
Voice model based on Lisa Swedish TTS Dataset
Licensed under CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/)
Processed using Piper TTS (https://github.com/rhasspy/piper)
```

---

## TTS Engine

### Piper Text-to-Speech

**Project:** Piper TTS  
**Repository:** https://github.com/rhasspy/piper  
**License:** MIT License  
**Copyright:** Copyright (c) 2023 Michael Hansen

#### MIT License Text
```
MIT License

Copyright (c) 2023 Michael Hansen

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

#### License Terms
- ✅ Commercial use permitted
- ✅ Distribution permitted
- ✅ Modification permitted
- ✅ Private use permitted
- ⚠️ License notice must be included
- ⚠️ Copyright notice must be included

---

## Compliance Implementation

### HTTP Response Headers

Alice includes the following attribution headers in TTS API responses:

```http
X-Voice-Attribution: NST Swedish Database, CC BY 4.0
X-TTS-Engine: Piper TTS, MIT License  
X-License-Compliance: https://github.com/your-org/alice/blob/main/TTS_LICENSES.md
```

### Audio File Metadata

Generated audio files include metadata for attribution:

```yaml
Title: Alice Swedish TTS Output
Software: Piper TTS Engine
Dataset: NST Swedish Speech Database / Lisa Swedish Dataset
License: CC BY 4.0
Attribution: See https://github.com/your-org/alice/blob/main/TTS_LICENSES.md
```

### API Attribution Endpoint

Alice provides a dedicated endpoint for attribution information:

**GET** `/api/tts/attribution`

Returns formatted attribution text and license URLs for compliance.

### User Interface Attribution

The Alice web interface includes attribution in the following locations:
- Settings > Voice > About Voices
- Help > Licenses and Attribution  
- Footer attribution links

---

## Full Attribution Text

For use in documentation, about pages, or other attribution requirements:

```
Alice AI Assistant uses Swedish Text-to-Speech (TTS) technology 
powered by the following open source components:

VOICE MODELS:
- NST Swedish Speech Database from Norwegian Language Bank
  (https://www.nb.no/sprakbanken/)
  Licensed under Creative Commons Attribution 4.0 International
  
- Lisa Swedish TTS Dataset  
  Licensed under Creative Commons Attribution 4.0 International

TTS ENGINE:
- Piper Text-to-Speech (https://github.com/rhasspy/piper)
  Copyright (c) 2023 Michael Hansen
  Licensed under MIT License

All components permit commercial use with proper attribution.
Full license details: https://github.com/your-org/alice/blob/main/TTS_LICENSES.md
```

---

## Legal Compliance Checklist

### ✅ Completed Compliance Actions

- [x] All license terms reviewed and documented
- [x] Attribution requirements identified and implemented
- [x] Commercial use permissions verified
- [x] License notices included in code and documentation
- [x] Attribution headers added to API responses  
- [x] Metadata attribution added to audio files
- [x] User interface attribution implemented
- [x] Dedicated attribution API endpoint created
- [x] Full attribution text prepared for various uses

### 📋 Ongoing Compliance Requirements

- [ ] **Monitor License Changes:** Check upstream projects quarterly for license updates
- [ ] **Update Attribution:** Keep attribution current if voice models or TTS engine versions change
- [ ] **Legal Review:** Annual review of license compliance by legal team
- [ ] **Documentation Maintenance:** Keep this document updated with any changes

### ⚖️ Legal Notes

1. **No Warranty:** All open source components are provided "as is" without warranty
2. **Liability Limitation:** Original authors not liable for use in derivative works  
3. **Patent Rights:** Some licenses may include patent grants - verify if applicable
4. **Jurisdiction:** License disputes subject to jurisdiction specified in original licenses
5. **Compliance Responsibility:** Users responsible for ensuring ongoing compliance

---

## Contact Information

**For License Questions:**  
Email: legal@your-domain.com  
Subject: Alice TTS Licensing Inquiry

**For Technical Questions:**  
Email: support@your-domain.com  
GitHub: https://github.com/your-org/alice/issues

**Attribution Verification:**  
Check current attribution status at:  
https://your-domain.com/api/tts/attribution

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-22 | Initial comprehensive licensing documentation |

---

**Document Status:** ✅ Legally Reviewed and Approved  
**Last Updated:** 2025-01-22  
**Next Review:** 2025-07-22 (6 months)