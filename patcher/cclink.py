"""
Description: monitors a CC message for change and links it to a fluid setting or effects control
"""

class CCLink:

    def __init__(self, fluid, target, link, type, xfrm, **kwargs):
        self.fluid = fluid
        self.target = target
        self.channel, self.cc = map(int, link.split('/'))
        self.type = type
        self.xfrm = xfrm
        for a in kwargs:
            setattr(self, a, kwargs[a])
        self.val = self.fluid.get_cc(self.channel - 1, self.cc)

    def haschanged(self):
        val = self.fluid.get_cc(self.channel - 1, self.cc)
        if val != self.val:
            self.val = val
            return True
        else:
            return False
            
