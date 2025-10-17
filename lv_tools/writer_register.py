from omni.replicator.core import WriterRegistry
from isaacsim.replicator.writers import PoseWriter
# PoseWriter
WriterRegistry.register(PoseWriter)
(
    WriterRegistry._default_writers.append("PoseWriter")
    if "PoseWriter" not in WriterRegistry._default_writers
    else None
)


'''

from omni.replicator.core import WriterRegistry
from isaacsim.replicator.writers import PoseWriter

# PoseWriter
WriterRegistry.register(PoseWriter)
(
    WriterRegistry._default_writers.append("PoseWriter")
    if "PoseWriter" not in WriterRegistry._default_writers
    else None
)

'''