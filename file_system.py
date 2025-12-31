class Block:
    def __init__(self, size=1024):
        self.size=size
        self.used=0
        self.files={}
        self.next=None
        self.fragments=[]

class FileAllocationTable:
    def __init__(self, total_blocks=1024):
        self.total_blocks=total_blocks
        self.blocks=[Block() for _ in range(total_blocks)]
        self.file_table={}
        self.current_method="continuous"
        
    def set_allocation_method(self, method):
        if method in ["continuous", "linked", "indexed"]:
            self.current_method = method
            return True
        return False

    def get_free_blocks(self, size):
        free_blocks=[]
        for i, block in enumerate(self.blocks):
            if block.used==0:
                free_blocks.append(i)
                if len(free_blocks)* block.size>=size:
                    break
        return free_blocks

    def allocate_continuous(self, filename, size):
        blocks_needed=(size + self.blocks[0].size-1)//self.blocks[0].size
        free_blocks=[]
        current_sequence=[]
        for i, block in enumerate(self.blocks):
            if block.used==0:
                current_sequence.append(i)
                if len(current_sequence)==blocks_needed:
                    free_blocks=current_sequence
                    break
            else:
                current_sequence=[]

        if len(free_blocks)==blocks_needed:
            for block_num in free_blocks:
                self.blocks[block_num].used=1
                self.blocks[block_num].files[filename]=size
            self.file_table[filename]={
                'blocks':free_blocks,
                'size':size,
                'method':'continuous'
            }
            return True
        return False

    def allocate_linked(self, filename, size):
        blocks_needed=(size+self.blocks[0].size-1)//self.blocks[0].size
        allocated_blocks=[]
        prev_block=None

        for i, block in enumerate(self.blocks):
            if block.used==0:
                block.used=1
                block.files[filename]=size
                allocated_blocks.append(i)
                if prev_block is not None:
                    self.blocks[prev_block].next=i
                prev_block=i
                if len(allocated_blocks)==blocks_needed:
                    break

        if len(allocated_blocks)==blocks_needed:
            self.file_table[filename]={
                'blocks':allocated_blocks,
                'size':size,
                'method':'linked'
            }
            return True
        
        for block_num in allocated_blocks:
            self.blocks[block_num].used=0
            self.blocks[block_num].files.pop(filename,None)
            self.blocks[block_num].next=None
        return False

    def allocate_indexed(self, filename, size):
        blocks_needed=(size+self.blocks[0].size-1)//self.blocks[0].size
        free_blocks=self.get_free_blocks(size+self.blocks[0].size)
        if len(free_blocks)>blocks_needed:
            index_block=free_blocks[0]
            data_blocks=free_blocks[1:blocks_needed+1]
            self.blocks[index_block].used=1
            self.blocks[index_block].files[filename]=size
            self.blocks[index_block].fragments=data_blocks
            for block_num in data_blocks:
                self.blocks[block_num].used=1
                self.blocks[block_num].files[filename]=size
            self.file_table[filename]= {
                'index_block': index_block,
                'data_blocks': data_blocks,
                'size': size,
                'method': 'indexed'
            }
            return True
        return False

    def allocate_file(self, filename, size):
        if filename in self.file_table:
            return False, "File already exists"
            
        if self.current_method=="continuous":
            success=self.allocate_continuous(filename,size)
        elif self.current_method=="linked":
            success=self.allocate_linked(filename,size)
        else:
            success=self.allocate_indexed(filename,size)
            
        if success:
            return True, "File allocated successfully"
        return False, "Not enough space"

    def deallocate_file(self, filename):
        if filename not in self.file_table:
            return False
        file_info=self.file_table[filename]
        if file_info['method'] in ['continuous', 'linked']:
            for block_num in file_info['blocks']:
                self.blocks[block_num].used=0
                self.blocks[block_num].files.pop(filename, None)
                self.blocks[block_num].next=None
        else:
            index_block=file_info['index_block']
            self.blocks[index_block].used =0
            self.blocks[index_block].files.pop(filename, None)
            self.blocks[index_block].fragments=[]
            
            for block_num in file_info['data_blocks']:
                self.blocks[block_num].used=0
                self.blocks[block_num].files.pop(filename, None)
        
        del self.file_table[filename]
        return True

    def get_fragmentation_info(self):
        total_free_blocks=sum(1 for block in self.blocks if block.used==0)
        free_segments=[]
        current_segment=0
        
        for block in self.blocks:
            if block.used==0:
                current_segment+=1
            elif current_segment>0:
                free_segments.append(current_segment)
                current_segment=0
                
        if current_segment>0:
            free_segments.append(current_segment)
            
        return {
            'total_blocks': self.total_blocks,
            'free_blocks': total_free_blocks,
            'used_blocks': self.total_blocks - total_free_blocks,
            'free_segments': len(free_segments),
            'largest_free_segment': max(free_segments) if free_segments else 0,
            'average_free_segment': sum(free_segments) / len(free_segments) if free_segments else 0,
            'fragmentation_percentage': (1 - (max(free_segments) if free_segments else 0) / total_free_blocks) * 100 if total_free_blocks > 0 else 0
        }

    def get_file_layout(self):
        layout=[]
        for i, block in enumerate(self.blocks):
            block_info = {
                'block_num': i,
                'used': block.used,
                'files': list(block.files.keys()),
                'next': block.next,
                'fragments': block.fragments
            }
            layout.append(block_info)
        return layout