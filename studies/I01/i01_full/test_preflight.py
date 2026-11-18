"""CPU-only contract checks for wheel filename / Python compatibility preflight."""
import unittest
from run import accepts, preflight_for
from analyze import python_version_key


def release(filename,requires_python=None,yanked=False):
    return {'status':'ok','requires_python':None,
            'files':[{'filename':filename,'packagetype':'bdist_wheel',
                      'requires_python':requires_python,'yanked':yanked}]}


class PreflightTest(unittest.TestCase):
    def test_pure_python_wheel_works_on_all_platforms(self):
        sample=release('example-1.0-py3-none-any.whl')
        for py in ['3.8','3.10','3.12','3.14']:
            for plat in ['linux_amd64','windows_amd64','macos_arm64']:
                self.assertTrue(preflight_for(sample,py,plat)['b2_root_gate'])

    def test_platform_specific_abi(self):
        sample=release('example-1.0-cp310-cp310-win_amd64.whl')
        self.assertTrue(preflight_for(sample,'3.10','windows_amd64')['b2_root_gate'])
        self.assertFalse(preflight_for(sample,'3.10','linux_amd64')['b2_root_gate'])
        self.assertFalse(preflight_for(sample,'3.12','windows_amd64')['b2_root_gate'])

    def test_requires_python_on_wheel(self):
        sample=release('example-1.0-py3-none-any.whl','>=3.11')
        self.assertFalse(preflight_for(sample,'3.8','windows_amd64')['b2_root_gate'])
        self.assertTrue(preflight_for(sample,'3.12','windows_amd64')['b2_root_gate'])
        self.assertFalse(accepts('>=3.11','3.10'))

    def test_yanked_policy_is_explicit(self):
        self.assertFalse(preflight_for(release('example-1.0-py3-none-any.whl',yanked=True),
                                       '3.12','linux_amd64')['b2_root_gate'])

    def test_no_metadata_is_unknown(self):
        sample={'status':'http_404','files':[]}
        self.assertIsNone(preflight_for(sample,'3.10','windows_amd64')['b2_root_gate'])

    def test_python_minor_version_order_not_float_order(self):
        versions=[{'python':v} for v in ('3.14','3.8','3.12','3.10')]
        ordered=sorted(versions,key=python_version_key)
        self.assertEqual([x['python'] for x in ordered],
                         ['3.8','3.10','3.12','3.14'])


if __name__=='__main__':unittest.main()
