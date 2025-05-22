# Project Writeup

## Approach & Assumptions
The script automates product extraction from construction submittal PDFs using OpenAI Vision. It converts each PDF page into a base64-encoded image and feeds it into the GPT-4 Vision API, prompting it to identify structured product entries. I assumed that valid products would contain model numbers (usually with digits) and that manufacturer names might not always appear on the same page as the product. To clean and unify the output, I included filtering for non-product entries, normalization of inconsistent strings, and deduplication. I also accounted for potential formatting noise by extracting the last segment of a multi-part manufacturer string and handling unspecified values gracefully.



## Limitations & Future Improvements

- Cross-page context: Manufacturer inference still depends on the page-level response from GPT. A more advanced system could track manufacturer context across pages.
- Multimodal consistency: GPT-4 Vision responses can vary slightly even for similar inputs. Adding a fallback rule-based system for common products could improve reliability. Notice there is an occasional entry for something not in the pdf. If given more time I would refine this system to ensure accuracy. 
- Performance: The current implementation processes pages sequentially; a parallelized or batched version could reduce processing time for large PDFs.
- Structured output control: Adding fine-tuned examples or embedding visual cues in prompts could further improve extraction precision.
