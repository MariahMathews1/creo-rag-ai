# V1 Demo Walkthrough

This walkthrough uses fictional data and must not be used to configure or operate a machine.

## Prepare the demo

```bash
make migrate
make seed-v1-demo
make dev
```

Open the app, select **R&D FANUC Lathe Demo**, and open **RL-200 FANUC 0i-TF Demo Post**.

## Recommended story

1. Start on **Overview**. Explain that the Post Record is an engineering development record, then use its primary next action.
2. Open **Machine Knowledge**. Show confirmed spindle facts beside the proposed G74 fact. Open the source reference and explain that proposed evidence is not confirmed knowledge.
3. Open **OFG Configuration**. Show Maximum Spindle Speed and its `Manual / Document → Machine Fact → OFG Setting` traceability. Point out that the OFG menu path is not yet verified.
4. Open the Tool Change Sequence setting to show the applied **Tool Change Safe Retract** site standard.
5. Open Cycle Support to show why custom logic is required. The implementation is deliberately recorded as undetermined; FIL/CIMFIL remains a possibility requiring site verification.
6. Open **Review**. Show outstanding items and the three compact validation stages. These are manually recorded results; the app does not launch G-POST or VERICUT.
7. Select **Export Package**. Review the package contents and the explicit notice that the export is not a native G-POST postprocessor file.

## Demo boundary

All KLS manual language, controller details, engineering decisions, and standards in this dataset are fictional. No production CL/NCL, G-code, geometry, toolpath, or machine authorization is included.
