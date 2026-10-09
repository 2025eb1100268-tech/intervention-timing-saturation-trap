# Transcript timestamps against hook timestamps

202 calls logged by both instruments, across 24 runs (16 Phase-9C, 8 Phase-9D).

| offset (hook ts minus transcript ts) | median | min | max | max abs |
|---|---|---|---|---|
| vs the line carrying the RESULT | -0.010 s | -0.931 s | -0.007 s | 0.931 s |
| vs the line ISSUING the call | +0.187 s | +0.089 s | +138.537 s | 138.537 s |

| run | transcript calls | matched | median offset (result) | max abs offset (result) | median offset (issue) | unmatched calls |
|---|---|---|---|---|---|---|
| S02_fable | 7 | 6 | -0.456 s | 0.915 s | +0.119 s | ok |
| S02_opus | 7 | 7 | -0.009 s | 0.926 s | +0.123 s | ok |
| S02_opus55 | 10 | 9 | -0.010 s | 0.912 s | +0.168 s | ok |
| S03_fable | 9 | 7 | -0.012 s | 0.926 s | +0.120 s | ok |
| S03_opus | 10 | 10 | -0.009 s | 0.924 s | +0.174 s | ok |
| S03_opus55 | 8 | 7 | -0.013 s | 0.916 s | +0.123 s | ok |
| S05_fable | 7 | 5 | -0.910 s | 0.913 s | +0.131 s | ok |
| S05_opus | 14 | 14 | -0.009 s | 0.925 s | +0.145 s | ok |
| S05_opus55 | 9 | 9 | -0.011 s | 0.919 s | +2.062 s | ok |
| S06_fable | 5 | 5 | -0.010 s | 0.913 s | +0.152 s | ok |
| S06_opus | 6 | 6 | -0.009 s | 0.917 s | +1.504 s | ok |
| S06_opus55 | 4 | 3 | -0.015 s | 0.914 s | +0.125 s | ok |
| S07_fable | 8 | 8 | -0.012 s | 0.925 s | +0.131 s | ok |
| S07_opus | 9 | 9 | -0.008 s | 0.924 s | +0.118 s | ok |
| S07_opus55 | 8 | 7 | -0.012 s | 0.892 s | +0.173 s | ok |
| S08_fable | 7 | 6 | -0.009 s | 0.921 s | +0.293 s | ok |
| S08_opus | 12 | 12 | -0.009 s | 0.917 s | +5.674 s | ok |
| S08_opus55 | 8 | 8 | -0.016 s | 0.915 s | +2.399 s | ok |
| S09_fable | 17 | 17 | -0.009 s | 0.931 s | +0.423 s | ok |
| S09_opus | 20 | 20 | -0.010 s | 0.923 s | +0.242 s | ok |
| S09_opus55 | 12 | 12 | -0.011 s | 0.912 s | +0.328 s | ok |
| S10_fable | 4 | 4 | -0.009 s | 0.908 s | +4.650 s | ok |
| S10_opus | 5 | 5 | -0.013 s | 0.918 s | +7.273 s | ok |
| S10_opus55 | 7 | 6 | -0.012 s | 0.911 s | +0.173 s | ok |
