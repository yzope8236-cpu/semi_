import os
import json
import time

try:
    from Semi_ATE import STDF
    HAVE_SEMI_ATE = True
except ImportError:
    HAVE_SEMI_ATE = False

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'samples', 'stdf-golden')
EXPECTED_DIR = os.path.join(OUTPUT_DIR, 'expected')

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(EXPECTED_DIR, exist_ok=True)

class SyntheticSTDFGenerator:
    def __init__(self):
        if not HAVE_SEMI_ATE:
            raise ImportError("Semi-ATE-STDF library is required to generate fixtures.")
            
    def _write_record(self, f, record):
        if hasattr(record, 'pack'):
            f.write(record.pack())
        elif hasattr(record, 'to_binary'):
            f.write(record.to_binary())
        elif hasattr(record, '__repr__'):
            rep = record.__repr__()
            if isinstance(rep, str):
                f.write(rep.encode('latin1'))
            else:
                f.write(rep)
        else:
            raise ValueError(f"Cannot serialize record {type(record).__name__}")

    def _write_ptr(self, f, test_num, site_num, test_flag_list, parm_flag_list, result, test_name, lo_limit, hi_limit, units):
        ptr = STDF.PTR()
        ptr.set_value("TEST_NUM", int(test_num))
        ptr.set_value("HEAD_NUM", 1)
        ptr.set_value("SITE_NUM", int(site_num))
        
        ptr.set_value("TEST_FLG", test_flag_list)
        ptr.set_value("PARM_FLG", parm_flag_list)
        ptr.set_value("OPT_FLAG", ["0", "0", "0", "0", "0", "0", "0", "0"])
        
        ptr.set_value("RESULT", float(result))
        ptr.set_value("TEST_TXT", str(test_name))
        ptr.set_value("LO_LIMIT", float(lo_limit))
        ptr.set_value("HI_LIMIT", float(hi_limit))
        ptr.set_value("UNITS", str(units))
        
        assert ptr.to_dict()["TEST_NUM"] is not None, "PTR TEST_NUM was not initialized"
        self._write_record(f, ptr)

    def _write_device_attempt(self, f, site, x, y, passed, hbin, sbin, part_id):
        # PIR
        pir = STDF.PIR()
        pir.set_value("HEAD_NUM", 1)
        pir.set_value("SITE_NUM", site)
        self._write_record(f, pir)
        
        pass_test_flag = ["0", "0", "0", "0", "0", "0", "0", "0"]
        normal_parm_flag = ["0", "0", "0", "0", "0", "0", "0", "0"]
        fail_test_flag = ["0", "0", "0", "0", "0", "0", "0", "1"]
        high_limit_failure_parm_flag = ["0", "0", "0", "1", "0", "0", "0", "0"]
        low_limit_failure_parm_flag = ["0", "0", "0", "0", "1", "0", "0", "0"]
        
        # PTR 1: IDDQ (TEST_NUM = 101)
        iddq_test_flag = pass_test_flag if passed else fail_test_flag
        iddq_parm_flag = normal_parm_flag if passed else high_limit_failure_parm_flag
        iddq_res = 0.82 if passed else 1.45
        self._write_ptr(f, 101, site, iddq_test_flag, iddq_parm_flag, iddq_res, "IDDQ", 0.5, 1.2, "mA")
        
        # PTR 2: VTH (TEST_NUM = 202)
        vth_test_flag = pass_test_flag if passed else fail_test_flag
        vth_parm_flag = normal_parm_flag if passed else low_limit_failure_parm_flag
        vth_res = 0.72 if passed else 0.61
        self._write_ptr(f, 202, site, vth_test_flag, vth_parm_flag, vth_res, "VTH", 0.65, 0.85, "V")
        
        # PRR
        prr = STDF.PRR()
        prr.set_value("HEAD_NUM", 1)
        prr.set_value("SITE_NUM", site)
        # PART_FLG is a B*1 bit field. Use bit list (bit 3 indicates failure in STDF V4).
        part_flg = ["0", "0", "0", "0", "0", "0", "0", "0"] if passed else ["0", "0", "0", "1", "0", "0", "0", "0"]
        prr.set_value("PART_FLG", part_flg)
        prr.set_value("NUM_TEST", 2)
        prr.set_value("HARD_BIN", hbin)
        prr.set_value("SOFT_BIN", sbin)
        prr.set_value("X_COORD", x)
        prr.set_value("Y_COORD", y)
        prr.set_value("TEST_T", 100)
        prr.set_value("PART_ID", part_id)
        prr.set_value("PART_TXT", "")
        self._write_record(f, prr)

    def _write_summaries(self, f, wafer_id, dev_cnt, pass_cnt, fail_cnt, bins):

        wrr = STDF.WRR()
        wrr.set_value("HEAD_NUM", 1)
        wrr.set_value("SITE_GRP", 255)
        wrr.set_value("FINISH_T", int(time.time()))
        wrr.set_value("PART_CNT", dev_cnt)
        wrr.set_value("RTST_CNT", 0)
        wrr.set_value("ABRT_CNT", 0)
        wrr.set_value("GOOD_CNT", pass_cnt)
        wrr.set_value("FUNC_CNT", 0)
        wrr.set_value("WAFER_ID", wafer_id)
        self._write_record(f, wrr)
        
        mrr = STDF.MRR()
        mrr.set_value("FINISH_T", int(time.time()))
        mrr.set_value("DISP_COD", " ")
        mrr.set_value("USR_DESC", "")
        mrr.set_value("EXC_DESC", "")
        self._write_record(f, mrr)

    def generate_01_clean_single_wafer(self):
        filename = "01_clean_single_wafer.stdf"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'wb') as f:
            far = STDF.FAR(); far.set_value("CPU_TYPE", 2); far.set_value("STDF_VER", 4); self._write_record(f, far)
            mir = STDF.MIR(); mir.set_value("SETUP_T", int(time.time())); mir.set_value("START_T", int(time.time())); mir.set_value("STAT_NUM", 1); mir.set_value("MODE_COD", " "); mir.set_value("RTST_COD", " "); mir.set_value("PROT_COD", " "); mir.set_value("BURN_TIM", 0); mir.set_value("CMOD_COD", " "); mir.set_value("LOT_ID", "SYN-LOT-01"); mir.set_value("PART_TYP", "SYN-PART-1"); mir.set_value("NODE_NAM", "SYN-TESTER"); mir.set_value("TSTR_TYP", "SYN-TSTR"); self._write_record(f, mir)
            wir = STDF.WIR(); wir.set_value("HEAD_NUM", 1); wir.set_value("SITE_GRP", 255); wir.set_value("START_T", int(time.time())); wir.set_value("WAFER_ID", "WAF-01"); self._write_record(f, wir)
            
            for i in range(16):
                x, y = i % 4, i // 4
                passed = i not in [5, 10]
                hbin = 1 if passed else 10
                self._write_device_attempt(f, 1, x, y, passed, hbin, hbin, f"DEV_{i}")
                
            self._write_summaries(f, "WAF-01", 16, 14, 2, {"1": 14, "10": 2})

    def generate_02_edge_failure_cluster(self):
        filename = "02_edge_failure_cluster.stdf"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'wb') as f:
            far = STDF.FAR(); far.set_value("CPU_TYPE", 2); far.set_value("STDF_VER", 4); self._write_record(f, far)
            mir = STDF.MIR(); mir.set_value("SETUP_T", int(time.time())); mir.set_value("START_T", int(time.time())); mir.set_value("STAT_NUM", 1); mir.set_value("MODE_COD", " "); mir.set_value("RTST_COD", " "); mir.set_value("PROT_COD", " "); mir.set_value("BURN_TIM", 0); mir.set_value("CMOD_COD", " "); mir.set_value("LOT_ID", "SYN-LOT-02"); mir.set_value("PART_TYP", "SYN-PART-2"); mir.set_value("NODE_NAM", "SYN-TESTER"); mir.set_value("TSTR_TYP", "SYN-TSTR"); self._write_record(f, mir)
            wir = STDF.WIR(); wir.set_value("HEAD_NUM", 1); wir.set_value("SITE_GRP", 255); wir.set_value("START_T", int(time.time())); wir.set_value("WAFER_ID", "WAF-02"); self._write_record(f, wir)
            
            for i in range(100):
                x, y = i % 10, i // 10
                passed = i >= 20
                hbin = 1 if passed else 8
                self._write_device_attempt(f, 1, x, y, passed, hbin, hbin, f"DEV_{i}")
                
            self._write_summaries(f, "WAF-02", 100, 80, 20, {"1": 80, "8": 20})

    def generate_03_retest_devices(self):
        filename = "03_retest_devices.stdf"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'wb') as f:
            far = STDF.FAR(); far.set_value("CPU_TYPE", 2); far.set_value("STDF_VER", 4); self._write_record(f, far)
            mir = STDF.MIR(); mir.set_value("SETUP_T", int(time.time())); mir.set_value("START_T", int(time.time())); mir.set_value("STAT_NUM", 1); mir.set_value("MODE_COD", " "); mir.set_value("RTST_COD", " "); mir.set_value("PROT_COD", " "); mir.set_value("BURN_TIM", 0); mir.set_value("CMOD_COD", " "); mir.set_value("LOT_ID", "SYN-LOT-03"); mir.set_value("PART_TYP", "SYN-PART-3"); mir.set_value("NODE_NAM", "SYN-TESTER"); mir.set_value("TSTR_TYP", "SYN-TSTR"); self._write_record(f, mir)
            wir = STDF.WIR(); wir.set_value("HEAD_NUM", 1); wir.set_value("SITE_GRP", 255); wir.set_value("START_T", int(time.time())); wir.set_value("WAFER_ID", "WAF-03"); self._write_record(f, wir)
            
            # Dev 0: fail first attempt
            self._write_device_attempt(f, 1, 0, 0, False, 8, 8, "DEV_0")
            # Dev 0: pass second attempt (retest)
            self._write_device_attempt(f, 1, 0, 0, True, 1, 1, "DEV_0")
            # Dev 1: pass first attempt
            self._write_device_attempt(f, 1, 1, 0, True, 1, 1, "DEV_1")

            self._write_summaries(f, "WAF-03", 2, 2, 0, {"1": 2})

    def generate_04_multi_site_bins(self):
        filename = "04_multi_site_bins.stdf"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'wb') as f:
            far = STDF.FAR(); far.set_value("CPU_TYPE", 2); far.set_value("STDF_VER", 4); self._write_record(f, far)
            mir = STDF.MIR(); mir.set_value("SETUP_T", int(time.time())); mir.set_value("START_T", int(time.time())); mir.set_value("STAT_NUM", 1); mir.set_value("MODE_COD", " "); mir.set_value("RTST_COD", " "); mir.set_value("PROT_COD", " "); mir.set_value("BURN_TIM", 0); mir.set_value("CMOD_COD", " "); mir.set_value("LOT_ID", "SYN-LOT-04"); mir.set_value("PART_TYP", "SYN-PART-4"); mir.set_value("NODE_NAM", "SYN-TESTER"); mir.set_value("TSTR_TYP", "SYN-TSTR"); self._write_record(f, mir)
            wir = STDF.WIR(); wir.set_value("HEAD_NUM", 1); wir.set_value("SITE_GRP", 255); wir.set_value("START_T", int(time.time())); wir.set_value("WAFER_ID", "WAF-04"); self._write_record(f, wir)
            
            bins = {"1": 2, "7": 1, "9": 1}
            for i, (site, hbin) in enumerate(zip([1, 2, 3, 4], [1, 1, 7, 9])):
                passed = (hbin == 1)
                self._write_device_attempt(f, site, i, 0, passed, hbin, hbin, f"DEV_{i}")

            self._write_summaries(f, "WAF-04", 4, 2, 2, bins)

    def generate_all(self):
        print("Generating synthetic STDF fixtures...")
        self.generate_01_clean_single_wafer()
        self.generate_02_edge_failure_cluster()
        self.generate_03_retest_devices()
        self.generate_04_multi_site_bins()
        print("Done.")

if __name__ == "__main__":
    ensure_dirs()
    generator = SyntheticSTDFGenerator()
    generator.generate_all()
