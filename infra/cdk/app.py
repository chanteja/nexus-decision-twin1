#!/usr/bin/env python3
import aws_cdk as cdk
from nexus_stack import NexusDecisionTwinStack

app = cdk.App()
NexusDecisionTwinStack(app, "NexusDecisionTwinStack")
app.synth()
