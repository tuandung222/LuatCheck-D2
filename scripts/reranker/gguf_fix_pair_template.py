#!/usr/bin/env python3
"""Fix the XLM-RoBERTa sentence-pair template in a reranker GGUF.

HF encodes a (query, passage) pair for XLM-R models as ``<s> query </s></s> passage </s>``.  llama-server builds the
rerank prompt as ``[BOS if add_bos] query [EOS if add_eos] [SEP if add_sep] passage [EOS if add_eos]``.  The GGUF written
by convert_hf_to_gguf.py for XLMRobertaForSequenceClassification carries neither ``add_bos_token`` nor a separator
(the unigram tokenizer defaults to add_bos=false, add_eos=true), so the server would send ``query </s> passage </s>``
(``<s>`` and one ``</s>`` missing) and the scores no longer match the HF model (measured: logit 1.45 -> -3.42 on a
short pair, with the encoder output itself identical, cos >= 0.9999998, when given the HF token ids).  This script
copies the GGUF and sets ``tokenizer.ggml.add_bos_token`` = true, ``tokenizer.ggml.seperator_token_id`` (spelled like
this in llama.cpp) = the EOS id and ``tokenizer.ggml.add_sep_token`` = true, which makes the server produce exactly
the HF token sequence.

usage: gguf_fix_pair_template.py IN.gguf OUT.gguf [--gguf-py DIR]   (needs the `gguf` python package)
"""
import argparse
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--gguf-py", type=Path, help="path of llama.cpp/gguf-py (default: installed gguf package)")
    args = ap.parse_args()
    if args.gguf_py:
        sys.path.insert(0, str(args.gguf_py))
    import gguf
    from gguf.scripts.gguf_new_metadata import MetadataDetails, copy_with_new_metadata

    reader = gguf.GGUFReader(args.input, "r")
    arch = reader.get_field(gguf.Keys.General.ARCHITECTURE).contents()
    eos = reader.get_field(gguf.Keys.Tokenizer.EOS_ID).contents()
    writer = gguf.GGUFWriter(args.output, arch=arch, endianess=reader.endianess)
    alignment = reader.get_field(gguf.Keys.General.ALIGNMENT)
    if alignment is not None:
        writer.data_alignment = alignment.contents()
    new = {
        gguf.Keys.Tokenizer.SEP_ID: MetadataDetails(gguf.GGUFValueType.UINT32, int(eos), "XLM-R pair separator = </s>"),
        gguf.Keys.Tokenizer.ADD_SEP: MetadataDetails(gguf.GGUFValueType.BOOL, True),
        gguf.Keys.Tokenizer.ADD_BOS: MetadataDetails(gguf.GGUFValueType.BOOL, True),
    }
    copy_with_new_metadata(reader, writer, new, [])
    print(f"wrote {args.output} (add_bos_token = true, sep id = eos id = {eos}, add_sep_token = true)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
