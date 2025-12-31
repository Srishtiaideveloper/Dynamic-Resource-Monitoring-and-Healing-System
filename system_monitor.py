import psutil
import random
from collections import deque
import pandas as pd

class SystemProcessMonitor:
    def __init__(self):
        self.cpu_history=deque(maxlen=60)
        self.mem_history=deque(maxlen=60)
        self.time_history=deque(maxlen=60)

    def get_live_cpu_mem(self):
        cpu=psutil.cpu_percent(interval=0.1)
        mem=psutil.virtual_memory().percent
        timestamp=pd.Timestamp.now()
        self.cpu_history.append(cpu)
        self.mem_history.append(mem)
        self.time_history.append(timestamp)
        return list(self.time_history), list(self.cpu_history), list(self.mem_history)
        
    def get_all_processes(self):
        process_list=[]
        for proc in psutil.process_iter(['pid','name','cpu_percent','memory_percent']):
            try:
                process_list.append({
                    'pid':proc.info['pid'],
                    'name':proc.info['name'],
                    'cpu':proc.info['cpu_percent'],
                    'memory':round(proc.info['memory_percent'],2)
                })
            except: continue
        return sorted(process_list,key=lambda x:x['cpu'],reverse=True)
    
    def get_process_details(self,pid):
            try:
                proc=psutil.Process(pid)
                import pandas as pd
                return (
                    "Name: "+proc.name() +
                    "\nPID: "+str(proc.pid) +
                    "\nStatus: "+proc.status() +
                    "\nUser: "+proc.username() +
                    "\nCreated: "+str(pd.to_datetime(proc.create_time(), unit='s')) +
                    "\nCPU Usage: "+str(proc.cpu_percent(interval=0.1)) + " %" +
                    "\nMemory Usage: "+"{:.2f}".format(proc.memory_percent()) + " %" +
                    "\nThreads: "+str(proc.num_threads())
                )
            except: return "Process terminated or access denied."

class RealFileManager:
    def __init__(self):
        self.uploaded_files={}
        self.block_size=4096
        print("\n=== Initializing RealFileManager ===")
        print("Block size: "+str(self.block_size)+" bytes")
        memory=psutil.virtual_memory()
        self.total_disk_size=int(memory.total*0.8)
        self.used_space=0
        
    def get_available_space(self):
        return self.total_disk_size-self.used_space
        
    def can_accommodate_file(self, file_size):
        return file_size<=self.get_available_space()
    
    def analyze_file(self, filename, content):
        print("\nAnalyzing file: "+str(filename))
        print("Content type: "+str(type(content)))
        print("Content length: "+str(len(content) if content else 0)+" bytes")
        
        if not content:
            raise Exception("File content is empty")
            
        if not isinstance(content, (str, bytes, bytearray)):
            raise Exception(
                "Invalid content type: "+str(type(content))+". Expected string or bytes."
            )

        file_size=len(content)
        print("File size: "+"{:.2f}".format(file_size/1024)+" KB")

        if not self.can_accommodate_file(file_size):
            free_space_mb=self.get_available_space()/(1024*1024)
            raise Exception("Not enough space. Available space: "+"{:.2f}".format(free_space_mb)+" MB")

        num_blocks=(file_size+self.block_size-1)//self.block_size
        fragments=[]
        remaining_size=file_size
        current_pos=0
        max_fragment_size=min(
            remaining_size,
            self.block_size*(16 if file_size<1024*1024 else 8))
        
        while remaining_size > 0:
            if len(fragments)==0:
                max_blocks=min(remaining_size//self.block_size + 1, 16)
                fragment_blocks=random.randint(max_blocks // 2, max_blocks)
            else:
                max_blocks=min(remaining_size // self.block_size + 1, 8)
                fragment_blocks=random.randint(1, max_blocks)
            
            fragment_size=min(fragment_blocks * self.block_size, remaining_size)
            gap=random.randint(0,2) * self.block_size
            current_pos+=gap
            fragments.append({
                'start':current_pos,
                'size':fragment_size,
                'blocks':fragment_blocks
            })
            current_pos+=fragment_size
            remaining_size-=fragment_size
        base_fragmentation=(len(fragments)-1)/num_blocks*100
        size_factor=min(file_size/(10*1024*1024), 1) 
        fragmentation_score=base_fragmentation*(1+size_factor)
        
        file_info={
            'name':filename,
            'size':file_size,
            'num_blocks':num_blocks,
            'fragments':fragments,
            'fragmentation_score':min(fragmentation_score,100), 
            'allocated_space':current_pos
        }
        self.used_space+=file_info['allocated_space']
        self.uploaded_files[filename]=file_info
        return file_info
    
    def add_file(self, filename, content):
        file_size=len(content)
        self.uploaded_files[filename]={
            'content':content,
            'size':file_size,
            'num_blocks':(file_size + self.block_size - 1) // self.block_size,
            'fragments':[],
            'fragmentation_score':0,
            'allocated_space': file_size
        }
        self.used_space+=file_size

    def remove_file(self, filename):
        if filename in self.uploaded_files:
            file_info=self.uploaded_files[filename]
            self.used_space-=file_info['allocated_space']
            del self.uploaded_files[filename]
            return True
        return False
    
    def get_file_info(self, filename):
        return self.uploaded_files.get(filename)
    
    def get_all_files(self):
        return self.uploaded_files
    
    def get_storage_info(self):
        return {
            'total_size':self.total_disk_size,
            'used_space':self.used_space,
            'available_space':self.get_available_space(),
            'utilization':(self.used_space/self.total_disk_size)*100,
            'num_files':len(self.uploaded_files)
        }