# Gold vs predictions on test (24 examples)

BERT/JobBERT predictions are from seed 3477689. Spans are in square brackets. Selection is deterministic (random.Random(0)) among sentences of at most 30 tokens.

## 1. Skill – Dictionary: boundary error (source: house, idx 50)

- GOLD:     You [take a structured approach to work] and are skilled in [prioritising your tasks and identifying those that are the most important] .
- DICT:     You take a [structured] approach to work and are [skilled] in prioritising your tasks and identifying those that are the most important .
- BERT:     You take a [structured approach] to work and are skilled in [prioritising your tasks] and [identifying] those that are the most important .
- JOBBERT:  You take a [structured approach to work] and are skilled in [prioritising your tasks] and [identifying] those that are the most important .

## 2. Skill – Dictionary: boundary error (source: house, idx 54)

- GOLD:     The job entails [support and problem-solving] aboard vessels or at yards which will include much travel- activity .
- DICT:     The job entails support and [problem-solving] aboard vessels or at yards which will include much travel- activity .
- BERT:     The job entails [support and problem-solving] aboard vessels or at yards which will include much travel- activity .
- JOBBERT:  The job entails [support and problem-solving] aboard vessels or at yards which will include much travel- activity .

## 3. Skill – Dictionary misses, BERT finds it exactly (source: tech, idx 6)

- GOLD:     [performed code reviews] for your teammates
- DICT:     performed code reviews for your teammates
- BERT:     [performed code reviews] for your teammates
- JOBBERT:  [performed code reviews] for your teammates

## 4. Skill – Dictionary misses, BERT finds it exactly (source: tech, idx 22)

- GOLD:     * Knowledge of deployment approaches considerations and challenges of [managing deployments] across various environments
- DICT:     * Knowledge of deployment approaches considerations and challenges of managing deployments across various environments
- BERT:     * Knowledge of deployment approaches considerations and challenges of [managing deployments] across various environments
- JOBBERT:  * Knowledge of deployment approaches considerations and challenges of [managing deployments across various environments]

## 5. Skill – BERT: boundary error (source: house, idx 48)

- GOLD:     You will [set the direction] [coach and develop your team] .
- DICT:     You will set the direction coach and develop your team .
- BERT:     You will [set the direction coach] and [develop your team] .
- JOBBERT:  You will [set the direction] [coach and develop your team] .

## 6. Skill – BERT: boundary error (source: house, idx 46)

- GOLD:     You have a strong [business understanding] and is [strategic] [analytical] and [communicative] in how you approach tasks .
- DICT:     You have a strong [business understanding] and is strategic [analytical] and [communicative] in how you approach tasks .
- BERT:     You have a strong [business understanding] and is [strategic analytical] and [communicative] in how you approach tasks .
- JOBBERT:  You have a strong [business understanding] and is [strategic] [analytical] and [communicative] in how you approach [tasks] .

## 7. Skill – BERT: spurious prediction (source: house, idx 42)

- GOLD:     Motivated by overcoming obstacles and [continuously working on your own development] .
- DICT:     Motivated by overcoming obstacles and continuously working on your own development .
- BERT:     Motivated by [overcoming obstacles] and [continuously] [working on your own development] .
- JOBBERT:  Motivated by [overcoming obstacles] and continuously [working on your own development] .

## 8. Skill – BERT: spurious prediction (source: tech, idx 32)

- GOLD:     Contribute to the team's work with [high-quality well-tested and scalable code]
- DICT:     Contribute to the team's work with high-quality well-tested and scalable code
- BERT:     [Contribute to the team's work with] high-quality well-tested and scalable code
- JOBBERT:  [Contribute to the team's work] with high-quality well-tested and scalable code

## 9. Skill – JobBERT exact, BERT wrong (source: house, idx 52)

- GOLD:     The successful candidate will be a [credible] international sales professional ideally with experience from some of our business areas and with knowledge of the market place .
- DICT:     The successful candidate will be a credible international sales professional ideally with experience from some of our business areas and with knowledge of the market place .
- BERT:     The successful candidate will be a credible international sales professional ideally with experience from some of our business areas and with knowledge of the market place .
- JOBBERT:  The successful candidate will be a [credible] international sales professional ideally with experience from some of our business areas and with knowledge of the market place .

## 10. Skill – JobBERT exact, BERT wrong (source: house, idx 34)

- GOLD:     This entails [design execution and analysis of phosphoproteomics experiments] .
- DICT:     This entails design execution and analysis of phosphoproteomics experiments .
- BERT:     This entails design execution and [analysis of] phosphoproteomics [experiments] .
- JOBBERT:  This entails [design execution and analysis of phosphoproteomics experiments] .

## 11. Skill – BERT exact, JobBERT wrong (source: house, idx 54)

- GOLD:     About the job [Preventive maintenance of supplied equipment and machines] .
- DICT:     About the job Preventive maintenance of supplied equipment and machines .
- BERT:     About the job [Preventive maintenance of supplied equipment and machines] .
- JOBBERT:  About the job [Preventive] [maintenance of supplied equipment and machines] .

## 12. Skill – BERT exact, JobBERT wrong (source: tech, idx 21)

- GOLD:     [Testing] and [analysis of test results]
- DICT:     Testing and analysis of test results
- BERT:     [Testing] and [analysis of test results]
- JOBBERT:  [Testing and analysis of test results]

## 13. Knowledge – Dictionary: boundary error (source: house, idx 51)

- GOLD:     Having experience from [project management] [B2B market] [UX] and [development] will help you to succeed in that creative role .
- DICT:     Having experience from [project management] [B2B] market [UX] and development will help you to succeed in that creative role .
- BERT:     Having experience from [project management] [B2B market UX and development] will help you to succeed in that creative role .
- JOBBERT:  Having experience from [project management] [B2B market] [UX and development] will help you to succeed in that creative role .

## 14. Knowledge – Dictionary: boundary error (source: tech, idx 8)

- GOLD:     [django] [postgresql] [redis]
- DICT:     [django] [postgresql redis]
- BERT:     [django] [postgresql] [redis]
- JOBBERT:  [django] [postgresql] [redis]

## 15. Knowledge – Dictionary misses, BERT finds it exactly (source: tech, idx 21)

- GOLD:     [ASP.NET] [Blazor]
- DICT:     [ASP.NET] Blazor
- BERT:     ASP.NET [Blazor]
- JOBBERT:  [ASP.NET] [Blazor]

## 16. Knowledge – Dictionary misses, BERT finds it exactly (source: tech, idx 11)

- GOLD:     [c#] [f#] [typescript]
- DICT:     [c#] f# [typescript]
- BERT:     [c#] [f#] [typescript]
- JOBBERT:  [c#] [f#] [typescript]

## 17. Knowledge – BERT: boundary error (source: house, idx 53)

- GOLD:     Appreciation of the importance of [coherent software architecture and design] Loosely coupled [message or event based architectures] A full understanding of [eventual consistency concepts] preferably hands on experience
- DICT:     Appreciation of the importance of coherent [software architecture] and design Loosely coupled [message] or event based architectures A full understanding of eventual consistency concepts preferably hands on experience
- BERT:     Appreciation of the importance of [coherent software architecture] and [design] [Loosely coupled] [message or event based architectures] A full understanding of [eventual consistency concepts] preferably hands on experience
- JOBBERT:  Appreciation of the importance of [coherent software architecture and design] [Loosely coupled message or event based architectures] A full understanding of [eventual consistency] concepts preferably hands on experience

## 18. Knowledge – BERT: boundary error (source: tech, idx 4)

- GOLD:     • Experience of [Cloud Technologies] including [AWS] [containers] and [Kubernetes]
- DICT:     • Experience of [Cloud Technologies] including [AWS] containers and [Kubernetes]
- BERT:     • Experience of [Cloud Technologies] including [AWS containers] and [Kubernetes]
- JOBBERT:  • Experience of [Cloud Technologies] including [AWS containers] and [Kubernetes]

## 19. Knowledge – BERT: spurious prediction (source: house, idx 54)

- GOLD:     You have hands-on experience with <ORGANIZATION> <ORGANIZATION> products ( [decanters] [high-speed separators] [PureBilge] [FWG] [Pure Dry)] .
- DICT:     You have hands-on experience with <ORGANIZATION> <ORGANIZATION> products ( decanters high-speed separators PureBilge FWG Pure Dry) .
- BERT:     You have hands-on experience with [<ORGANIZATION>] [<ORGANIZATION>] products ( [decanters] [high-speed separators] [PureBilge] [FWG] [Pure Dry)] .
- JOBBERT:  You have hands-on experience with [<ORGANIZATION>] <ORGANIZATION> products ( [decanters] [high-speed separators] [PureBilge] [FWG] [Pure Dry)] .

## 20. Knowledge – BERT: spurious prediction (source: tech, idx 17)

- GOLD:     You are fluent in [Java] and have knowledge of other programming languages
- DICT:     You are fluent in [Java] and have knowledge of other programming languages
- BERT:     You are fluent in [Java] and have knowledge of other [programming] languages
- JOBBERT:  You are fluent in [Java] and have knowledge of other programming [languages]

## 21. Knowledge – JobBERT exact, BERT wrong (source: house, idx 57)

- GOLD:     [MATLAB] .
- DICT:     MATLAB .
- BERT:     MATLAB .
- JOBBERT:  [MATLAB] .

## 22. Knowledge – JobBERT exact, BERT wrong (source: house, idx 65)

- GOLD:     The subject area includes [feed evaluation] [digestive processes] [intermediary metabolism] and [impact of nutrition and feeding management] of productivity and [animal health] and [product quality] .
- DICT:     The subject area includes feed evaluation digestive processes intermediary metabolism and impact of nutrition and feeding management of productivity and animal health and product quality .
- BERT:     The subject area includes feed evaluation digestive processes intermediary metabolism and impact of nutrition and feeding management of productivity and animal health and product quality .
- JOBBERT:  The subject area includes [feed evaluation] [digestive processes] [intermediary metabolism] and impact of [nutrition] and [feeding management] of productivity and animal health and product quality .

## 23. Knowledge – BERT exact, JobBERT wrong (source: tech, idx 11)

- GOLD:     We take advantage of cloud services provided by AWS including but not limited to [functions as a service] [hosting] [messaging] [relational and non-relational databases] .
- DICT:     We take advantage of [cloud services] provided by [AWS] including but not limited to functions as a service hosting [messaging] [relational and non-relational databases] .
- BERT:     We take advantage of cloud services provided by [AWS] including but not limited to functions as a service hosting [messaging] [relational and non-relational databases] .
- JOBBERT:  We take advantage of cloud services provided by [AWS] including but not limited to [functions] as a service hosting messaging [relational and non-relational databases] .

## 24. Knowledge – BERT exact, JobBERT wrong (source: tech, idx 19)

- GOLD:     [java] [rest] [cloud] [spring] [design-patterns]
- DICT:     [java] [rest] cloud [spring] design-patterns
- BERT:     [java] [rest] [cloud] [spring] [design-patterns]
- JOBBERT:  [java] [rest] [cloud] [spring design-patterns]
